from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import (
    AttendanceAttempt,
    AttendanceRecord,
    AttendanceSession,
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
    MarkAttendanceRequest,
    MarkAttendanceResponse,
    SubjectOfferingOut,
    TimetableSlotOut,
)
from app.security import require_role
from app.utils import haversine_meters

router = APIRouter(prefix="/student", tags=["Student"])


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


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
    now = _utcnow()
    rows = db.scalars(
        select(AttendanceSession)
        .join(StudentEnrollment, StudentEnrollment.subject_offering_id == AttendanceSession.subject_offering_id)
        .where(
            StudentEnrollment.student_id == student.id,
            AttendanceSession.status == SessionStatus.active.value,
            AttendanceSession.ends_at > now.replace(tzinfo=None),
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
    now = _utcnow()

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

    if session.status != SessionStatus.active.value or _as_utc(session.ends_at) <= now:
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
