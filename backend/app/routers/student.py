from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import (
    AttendanceAttempt,
    AttendanceRecord,
    AttendanceSession,
    CondonationRequest,
    LeaveRequest,
    RequestStatus,
    SessionStatus,
    Student,
    StudentEnrollment,
    SubjectOffering,
    TimetableSlot,
)
from app.schemas import (
    ActiveSessionOut,
    AttendanceAlert,
    AttendanceRecordOut,
    AttendanceSummaryOut,
    CondonationRequestCreate,
    CondonationRequestOut,
    LeaveRequestCreate,
    LeaveRequestOut,
    MarkAttendanceRequest,
    MarkAttendanceResponse,
    SubjectOfferingOut,
    TimetableSlotOut,
)
from app.security import require_first_login_verified, require_role
from app.time_utils import as_utc, db_utc, utcnow
from app.utils import haversine_meters

router = APIRouter(prefix="/student", tags=["Student"], dependencies=[Depends(require_first_login_verified)])


def _offering_out(offering: SubjectOffering, enrollment_type: str | None = None) -> SubjectOfferingOut:
    return SubjectOfferingOut(
        id=offering.id,
        subject_code=offering.subject.subject_code,
        subject_name=offering.subject.subject_name,
        faculty_name=offering.faculty.name,
        faculty_id=offering.faculty_id,
        academic_year=offering.academic_year,
        semester_type=offering.semester_type,
        section=offering.section,
        semester=offering.semester,
        branch_id=offering.branch_id,
        branch_code=offering.branch.code if offering.branch else None,
        active=offering.active,
        enrollment_type=enrollment_type,
    )


# ---------------------------------------------------------------------------
# Subjects the student is enrolled in
# ---------------------------------------------------------------------------

@router.get("/subjects", response_model=list[SubjectOfferingOut])
def student_subjects(current=Depends(require_role("student")), db: Session = Depends(get_db)):
    student: Student = current["user"]
    rows = db.execute(
        select(SubjectOffering, StudentEnrollment.enrollment_type)
        .join(StudentEnrollment, StudentEnrollment.subject_offering_id == SubjectOffering.id)
        .where(StudentEnrollment.student_id == student.id, SubjectOffering.active.is_(True))
        .order_by(SubjectOffering.semester, SubjectOffering.section)
    ).all()
    return [_offering_out(offering, enrollment_type) for offering, enrollment_type in rows]


# ---------------------------------------------------------------------------
# Active sessions for enrolled subjects
# ---------------------------------------------------------------------------

@router.get("/active-sessions", response_model=list[ActiveSessionOut])
def student_active_sessions(current=Depends(require_role("student")), db: Session = Depends(get_db)):
    student: Student = current["user"]
    now = utcnow()
    rows = db.scalars(
        select(AttendanceSession)
        .join(StudentEnrollment, StudentEnrollment.subject_offering_id == AttendanceSession.subject_offering_id)
        .where(
            StudentEnrollment.student_id == student.id,
            AttendanceSession.status == SessionStatus.active.value,
            AttendanceSession.ends_at > db_utc(now),
        )
        .order_by(AttendanceSession.ends_at)
    ).all()
    return [
        ActiveSessionOut(
            id=s.id,
            subject_offering_id=s.subject_offering_id,
            subject_code=s.subject_offering.subject.subject_code,
            subject_name=s.subject_offering.subject.subject_name,
            faculty_name=s.faculty.name,
            session_type=s.session_type,
            starts_at=s.starts_at,
            ends_at=s.ends_at,
            radius_meters=s.radius_meters,
        )
        for s in rows
    ]


# ---------------------------------------------------------------------------
# Mark attendance
# ---------------------------------------------------------------------------

def _log_attempt(
    db: Session,
    request: Request,
    session_id: int | None,
    student_id: int,
    code_ok: bool,
    location_ok: bool,
    distance: float | None,
    device_id: str | None,
    result: str,
    reason: str,
) -> None:
    db.add(
        AttendanceAttempt(
            session_id=session_id,
            student_id=student_id,
            entered_code_valid=code_ok,
            location_valid=location_ok,
            distance_meters=distance,
            device_id=device_id,
            ip_address=request.client.host if request.client else None,
            result=result,
            reason=reason,
        )
    )
    db.commit()


@router.post("/attendance/mark", response_model=MarkAttendanceResponse)
def mark_attendance(
    payload: MarkAttendanceRequest,
    request: Request,
    current=Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    from app.security import verify_code

    student: Student = current["user"]
    session = db.get(AttendanceSession, payload.session_id)
    now = utcnow()

    if not session:
        _log_attempt(db, request, None, student.id, False, False, None, payload.device_id, "rejected", "session_not_found")
        raise HTTPException(status_code=404, detail="session_not_found")

    distance = haversine_meters(
        session.teacher_latitude, session.teacher_longitude,
        payload.student_latitude, payload.student_longitude,
    )
    code_ok = verify_code(payload.entered_code, session.code_hash)
    location_ok = distance <= session.radius_meters

    def reject(reason: str, status_code: int = 400):
        _log_attempt(db, request, session.id, student.id, code_ok, location_ok, distance, payload.device_id, "rejected", reason)
        raise HTTPException(status_code=status_code, detail=reason)

    failed_attempts = db.scalar(
        select(func.count(AttendanceAttempt.id)).where(
            AttendanceAttempt.session_id == session.id,
            AttendanceAttempt.student_id == student.id,
            AttendanceAttempt.result == "rejected",
            AttendanceAttempt.reason.in_(["invalid_code", "outside_radius", "poor_gps_accuracy"]),
        )
    ) or 0
    if failed_attempts >= 5:
        reject("attendance_locked_for_session", 423)

    if session.status != SessionStatus.active.value or as_utc(session.ends_at) <= now:
        reject("session_expired_or_inactive")

    enrolled = db.scalar(
        select(StudentEnrollment).where(
            StudentEnrollment.student_id == student.id,
            StudentEnrollment.subject_offering_id == session.subject_offering_id,
        )
    )
    if not enrolled:
        reject("not_enrolled", 403)

    existing = db.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.session_id == session.id,
            AttendanceRecord.student_id == student.id,
        )
    )
    if existing:
        reject("already_marked")
    if not code_ok:
        reject("invalid_code")
    if payload.gps_accuracy_meters > settings.max_gps_accuracy_meters:
        reject("poor_gps_accuracy")
    if not location_ok:
        reject("outside_radius")

    record = AttendanceRecord(
        session_id=session.id,
        student_id=student.id,
        student_latitude=payload.student_latitude,
        student_longitude=payload.student_longitude,
        gps_accuracy_meters=payload.gps_accuracy_meters,
        distance_from_teacher=distance,
        device_id=payload.device_id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    _log_attempt(db, request, session.id, student.id, True, True, distance, payload.device_id, "accepted", "present")
    return MarkAttendanceResponse(
        status=record.status,
        distance_from_teacher=round(distance, 2),
        marked_at=record.marked_at,
    )


# ---------------------------------------------------------------------------
# Attendance history
# ---------------------------------------------------------------------------

@router.get("/attendance/history", response_model=list[AttendanceRecordOut])
def student_history(current=Depends(require_role("student")), db: Session = Depends(get_db)):
    student: Student = current["user"]
    records = db.scalars(
        select(AttendanceRecord)
        .where(AttendanceRecord.student_id == student.id)
        .order_by(AttendanceRecord.marked_at.desc())
    ).all()
    return [
        AttendanceRecordOut(
            id=r.id,
            student_id=student.id,
            student_name=student.name,
            usn=student.usn,
            status=r.status,
            distance_from_teacher=round(r.distance_from_teacher, 2),
            marked_at=r.marked_at,
        )
        for r in records
    ]


# ---------------------------------------------------------------------------
# Attendance summary per subject
# ---------------------------------------------------------------------------

@router.get("/attendance/summary", response_model=list[AttendanceSummaryOut])
def student_summary(current=Depends(require_role("student")), db: Session = Depends(get_db)):
    student: Student = current["user"]
    enrollments = db.scalars(select(StudentEnrollment).where(StudentEnrollment.student_id == student.id)).all()
    summaries = []
    for enrollment in enrollments:
        offering = enrollment.subject_offering
        session_ids = db.scalars(
            select(AttendanceSession.id).where(
                AttendanceSession.subject_offering_id == offering.id,
                AttendanceSession.status.in_([SessionStatus.active.value, SessionStatus.ended.value, SessionStatus.expired.value]),
            )
        ).all()
        total = len(session_ids)
        present = 0
        if session_ids:
            present = db.scalar(
                select(func.count(AttendanceRecord.id)).where(
                    AttendanceRecord.student_id == student.id,
                    AttendanceRecord.session_id.in_(session_ids),
                    AttendanceRecord.status == "present",
                )
            ) or 0
        percentage = round((present / total) * 100, 2) if total else 0.0
        summaries.append(
            AttendanceSummaryOut(
                subject_offering_id=offering.id,
                subject_code=offering.subject.subject_code,
                subject_name=offering.subject.subject_name,
                total_sessions=total,
                present_sessions=present,
                percentage=percentage,
            )
        )
    return summaries


def _attendance_percentage(db: Session, student_id: int, offering_id: int) -> float:
    session_ids = db.scalars(
        select(AttendanceSession.id).where(
            AttendanceSession.subject_offering_id == offering_id,
            AttendanceSession.status.in_([SessionStatus.active.value, SessionStatus.ended.value, SessionStatus.expired.value]),
        )
    ).all()
    if not session_ids:
        return 0.0
    present = db.scalar(
        select(func.count(AttendanceRecord.id)).where(
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.session_id.in_(session_ids),
            AttendanceRecord.status == "present",
        )
    ) or 0
    return round((present / len(session_ids)) * 100, 2)


def _leave_out(req: LeaveRequest) -> LeaveRequestOut:
    return LeaveRequestOut(
        id=req.id,
        student_id=req.student_id,
        student_name=req.student.name,
        usn=req.student.usn,
        leave_type=req.leave_type,
        start_date=req.start_date,
        end_date=req.end_date,
        reason=req.reason,
        document_path=req.document_path,
        status=req.status,
        reviewed_by_name=req.reviewer.name if req.reviewer else None,
        reviewed_at=req.reviewed_at,
        created_at=req.created_at,
    )


def _condonation_out(req: CondonationRequest) -> CondonationRequestOut:
    return CondonationRequestOut(
        id=req.id,
        student_id=req.student_id,
        student_name=req.student.name,
        usn=req.student.usn,
        subject_offering_id=req.subject_offering_id,
        subject_code=req.subject_offering.subject.subject_code,
        subject_name=req.subject_offering.subject.subject_name,
        current_percentage=req.current_percentage,
        reason=req.reason,
        status=req.status,
        reviewed_by_name=req.reviewer.name if req.reviewer else None,
        reviewed_at=req.reviewed_at,
        created_at=req.created_at,
    )


@router.post("/leave-requests", response_model=LeaveRequestOut)
def create_leave_request(payload: LeaveRequestCreate, current=Depends(require_role("student")), db: Session = Depends(get_db)):
    student: Student = current["user"]
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=400, detail="end_date_before_start_date")
    req = LeaveRequest(
        student_id=student.id,
        leave_type=payload.leave_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason,
        document_path=payload.document_path,
        status=RequestStatus.pending.value,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return _leave_out(req)


@router.get("/leave-requests", response_model=list[LeaveRequestOut])
def list_leave_requests(current=Depends(require_role("student")), db: Session = Depends(get_db)):
    student: Student = current["user"]
    rows = db.scalars(select(LeaveRequest).where(LeaveRequest.student_id == student.id).order_by(LeaveRequest.created_at.desc())).all()
    return [_leave_out(r) for r in rows]


@router.post("/condonation-requests", response_model=CondonationRequestOut)
def create_condonation_request(payload: CondonationRequestCreate, current=Depends(require_role("student")), db: Session = Depends(get_db)):
    student: Student = current["user"]
    enrollment = db.scalar(
        select(StudentEnrollment).where(
            StudentEnrollment.student_id == student.id,
            StudentEnrollment.subject_offering_id == payload.subject_offering_id,
        )
    )
    if not enrollment:
        raise HTTPException(status_code=403, detail="not_enrolled")
    req = CondonationRequest(
        student_id=student.id,
        subject_offering_id=payload.subject_offering_id,
        current_percentage=_attendance_percentage(db, student.id, payload.subject_offering_id),
        reason=payload.reason,
        status=RequestStatus.pending.value,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return _condonation_out(req)


@router.get("/condonation-requests", response_model=list[CondonationRequestOut])
def list_condonation_requests(current=Depends(require_role("student")), db: Session = Depends(get_db)):
    student: Student = current["user"]
    rows = db.scalars(
        select(CondonationRequest).where(CondonationRequest.student_id == student.id).order_by(CondonationRequest.created_at.desc())
    ).all()
    return [_condonation_out(r) for r in rows]


# ---------------------------------------------------------------------------
# Attendance danger alerts (< 85% warning, < 75% critical)
# ---------------------------------------------------------------------------

@router.get("/alerts", response_model=list[AttendanceAlert])
def student_alerts(current=Depends(require_role("student")), db: Session = Depends(get_db)):
    student: Student = current["user"]
    summaries_resp = student_summary(current=current, db=db)
    alerts = []
    for s in summaries_resp:
        if s.total_sessions == 0:
            continue
        if s.percentage < 75:
            alerts.append(AttendanceAlert(
                subject_code=s.subject_code,
                subject_name=s.subject_name,
                percentage=s.percentage,
                level="critical",
            ))
        elif s.percentage < 85:
            alerts.append(AttendanceAlert(
                subject_code=s.subject_code,
                subject_name=s.subject_name,
                percentage=s.percentage,
                level="warning",
            ))
    return alerts


# ---------------------------------------------------------------------------
# Student timetable (today/week)
# ---------------------------------------------------------------------------

@router.get("/timetable", response_model=list[TimetableSlotOut])
def student_timetable(
    day: str | None = None,
    current=Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    student: Student = current["user"]
    # Get all offering IDs the student is enrolled in
    offering_ids = db.scalars(
        select(StudentEnrollment.subject_offering_id).where(StudentEnrollment.student_id == student.id)
    ).all()
    if not offering_ids:
        return []

    query = select(TimetableSlot).where(TimetableSlot.subject_offering_id.in_(offering_ids))
    if day:
        query = query.where(TimetableSlot.day_of_week == day.upper())

    slots = db.scalars(query.order_by(TimetableSlot.day_of_week, TimetableSlot.slot_number)).all()
    return [
        TimetableSlotOut(
            id=sl.id,
            subject_offering_id=sl.subject_offering_id,
            subject_code=sl.subject_offering.subject.subject_code,
            subject_name=sl.subject_offering.subject.subject_name,
            faculty_name=sl.subject_offering.faculty.name,
            day_of_week=sl.day_of_week,
            slot_number=sl.slot_number,
            start_time=sl.start_time,
            end_time=sl.end_time,
            room=sl.room,
            effective_from=sl.effective_from,
            effective_until=sl.effective_until,
        )
        for sl in slots
    ]
