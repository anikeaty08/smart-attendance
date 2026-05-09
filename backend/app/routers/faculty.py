from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import (
    AttendanceCorrection,
    AttendanceRecord,
    AttendanceSession,
    Faculty,
    SessionStatus,
    Student,
    StudentEnrollment,
    SubjectOffering,
)
from app.schemas import (
    ActiveSessionOut,
    AttendanceCorrectionOut,
    AttendanceCorrectionRequest,
    AttendanceRecordOut,
    AttendanceSummaryOut,
    StartSessionRequest,
    StartSessionResponse,
    SubjectOfferingOut,
)
from app.security import require_role
from app.utils import build_csv, generate_session_code
from app.security import hash_code

router = APIRouter(prefix="/faculty", tags=["Faculty"])


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _offering_out(offering: SubjectOffering) -> SubjectOfferingOut:
    from sqlalchemy import func, select as sa_select
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
    )


# ---------------------------------------------------------------------------
# Faculty's assigned offerings (including substitute assignments for today)
# ---------------------------------------------------------------------------

@router.get("/offerings", response_model=list[SubjectOfferingOut])
def faculty_offerings(current=Depends(require_role("faculty", "hod")), db: Session = Depends(get_db)):
    faculty: Faculty = current["user"]
    rows = db.scalars(
        select(SubjectOffering).where(
            SubjectOffering.faculty_id == faculty.id,
            SubjectOffering.active.is_(True),
        )
    ).all()
    return [_offering_out(r) for r in rows]


# ---------------------------------------------------------------------------
# Start attendance session
# ---------------------------------------------------------------------------

@router.post("/sessions/start", response_model=StartSessionResponse)
def start_session(
    payload: StartSessionRequest,
    current=Depends(require_role("faculty", "hod")),
    db: Session = Depends(get_db),
):
    faculty: Faculty = current["user"]
    offering = db.get(SubjectOffering, payload.subject_offering_id)

    # Faculty must own the offering OR have a substitute assignment for today
    from app.models import SubstituteAssignment
    today = _utcnow().date()
    is_substitute = db.scalar(
        select(SubstituteAssignment).where(
            SubstituteAssignment.subject_offering_id == payload.subject_offering_id,
            SubstituteAssignment.substitute_faculty_id == faculty.id,
            SubstituteAssignment.date == today,
        )
    )
    if not offering or (offering.faculty_id != faculty.id and not is_substitute):
        raise HTTPException(status_code=403, detail="offering_not_assigned_to_faculty")

    radius = min(max(payload.radius_meters, settings.default_radius_meters), settings.max_radius_meters)
    duration = max(1, min(payload.duration_minutes, 30))
    code = generate_session_code()
    now = _utcnow()
    session = AttendanceSession(
        subject_offering_id=offering.id,
        faculty_id=faculty.id,
        session_type=payload.session_type,
        code_hash=hash_code(code),
        teacher_latitude=payload.teacher_latitude,
        teacher_longitude=payload.teacher_longitude,
        radius_meters=radius,
        starts_at=now,
        ends_at=now + timedelta(minutes=duration),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return StartSessionResponse(
        id=session.id, code=code,
        starts_at=session.starts_at, ends_at=session.ends_at,
        radius_meters=radius,
    )


# ---------------------------------------------------------------------------
# Get / end session
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}", response_model=ActiveSessionOut)
def get_session(session_id: int, current=Depends(require_role("faculty", "hod")), db: Session = Depends(get_db)):
    faculty: Faculty = current["user"]
    session = db.get(AttendanceSession, session_id)
    if not session or session.faculty_id != faculty.id:
        raise HTTPException(status_code=404, detail="session_not_found")
    return ActiveSessionOut(
        id=session.id,
        subject_offering_id=session.subject_offering_id,
        subject_code=session.subject_offering.subject.subject_code,
        subject_name=session.subject_offering.subject.subject_name,
        faculty_name=session.faculty.name,
        session_type=session.session_type,
        starts_at=session.starts_at,
        ends_at=session.ends_at,
        radius_meters=session.radius_meters,
    )


@router.post("/sessions/{session_id}/end")
def end_session(session_id: int, current=Depends(require_role("faculty", "hod")), db: Session = Depends(get_db)):
    faculty: Faculty = current["user"]
    session = db.get(AttendanceSession, session_id)
    if not session or session.faculty_id != faculty.id:
        raise HTTPException(status_code=404, detail="session_not_found")
    session.status = SessionStatus.ended.value
    now = _utcnow().replace(tzinfo=None)
    session.ends_at = min(_as_utc(session.ends_at).replace(tzinfo=None), now)
    db.commit()
    return {"status": "ended", "session_id": session.id}


# ---------------------------------------------------------------------------
# Session attendance records
# ---------------------------------------------------------------------------

@router.get("/sessions/{session_id}/records", response_model=list[AttendanceRecordOut])
def session_records(session_id: int, current=Depends(require_role("faculty", "hod")), db: Session = Depends(get_db)):
    faculty: Faculty = current["user"]
    session = db.get(AttendanceSession, session_id)
    if not session or session.faculty_id != faculty.id:
        raise HTTPException(status_code=404, detail="session_not_found")
    records = db.scalars(select(AttendanceRecord).where(AttendanceRecord.session_id == session.id)).all()
    return [
        AttendanceRecordOut(
            id=r.id,
            student_id=r.student_id,
            student_name=r.student.name,
            usn=r.student.usn,
            status=r.status,
            distance_from_teacher=round(r.distance_from_teacher, 2),
            marked_at=r.marked_at,
        )
        for r in records
    ]


# ---------------------------------------------------------------------------
# Edit attendance record (with reason, 48h window enforced)
# ---------------------------------------------------------------------------

@router.put("/sessions/{session_id}/records/{student_id}", response_model=AttendanceCorrectionOut)
def correct_attendance(
    session_id: int,
    student_id: int,
    payload: AttendanceCorrectionRequest,
    current=Depends(require_role("faculty", "hod")),
    db: Session = Depends(get_db),
):
    faculty: Faculty = current["user"]
    session = db.get(AttendanceSession, session_id)
    if not session or session.faculty_id != faculty.id:
        raise HTTPException(status_code=404, detail="session_not_found")

    # 48-hour window check (HOD/Admin bypass via role — done in hod/admin routers)
    if current["role"] == "faculty":
        window = timedelta(hours=settings.correction_window_hours)
        if _utcnow() - _as_utc(session.starts_at) > window:
            raise HTTPException(status_code=403, detail="correction_window_expired")

    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="student_not_found")

    record = db.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.session_id == session_id,
            AttendanceRecord.student_id == student_id,
        )
    )
    old_status = record.status if record else "absent"

    if record:
        record.status = payload.new_status
    else:
        # Student was absent — create a manual record
        record = AttendanceRecord(
            session_id=session_id,
            student_id=student_id,
            status=payload.new_status,
            student_latitude=session.teacher_latitude,
            student_longitude=session.teacher_longitude,
            distance_from_teacher=0.0,
            verification_method="manual_correction",
        )
        db.add(record)
        db.flush()

    correction = AttendanceCorrection(
        record_id=record.id,
        session_id=session_id,
        student_id=student_id,
        old_status=old_status,
        new_status=payload.new_status,
        reason=payload.reason,
        corrected_by=faculty.id,
    )
    db.add(correction)
    db.commit()
    db.refresh(correction)

    return AttendanceCorrectionOut(
        id=correction.id,
        record_id=correction.record_id,
        session_id=session_id,
        student_id=student_id,
        student_name=student.name,
        usn=student.usn,
        old_status=old_status,
        new_status=payload.new_status,
        reason=payload.reason,
        corrected_by_name=faculty.name,
        corrected_at=correction.corrected_at,
    )


# ---------------------------------------------------------------------------
# Attendance summary across own subjects (for faculty's own view)
# ---------------------------------------------------------------------------

@router.get("/attendance/report", response_model=list[AttendanceSummaryOut])
def faculty_report(current=Depends(require_role("faculty", "hod")), db: Session = Depends(get_db)):
    faculty: Faculty = current["user"]
    offerings = db.scalars(
        select(SubjectOffering).where(
            SubjectOffering.faculty_id == faculty.id,
            SubjectOffering.active.is_(True),
        )
    ).all()

    result = []
    for offering in offerings:
        sessions = db.scalars(
            select(AttendanceSession.id).where(
                AttendanceSession.subject_offering_id == offering.id,
                AttendanceSession.status.in_(
                    [SessionStatus.active.value, SessionStatus.ended.value, SessionStatus.expired.value]
                ),
            )
        ).all()
        total = len(sessions)
        enrolled_count = db.scalar(
            select(StudentEnrollment).where(
                StudentEnrollment.subject_offering_id == offering.id
            ).with_only_columns(__import__("sqlalchemy").func.count())
        ) or 0
        result.append(
            AttendanceSummaryOut(
                subject_offering_id=offering.id,
                subject_code=offering.subject.subject_code,
                subject_name=offering.subject.subject_name,
                total_sessions=total,
                present_sessions=enrolled_count,
                percentage=0.0,
            )
        )
    return result


# ---------------------------------------------------------------------------
# Export attendance as CSV
# ---------------------------------------------------------------------------

@router.get("/export/attendance")
def export_attendance(
    offering_id: int,
    current=Depends(require_role("faculty", "hod")),
    db: Session = Depends(get_db),
):
    faculty: Faculty = current["user"]
    offering = db.get(SubjectOffering, offering_id)
    if not offering or offering.faculty_id != faculty.id:
        raise HTTPException(status_code=403, detail="access_denied")

    session_ids = db.scalars(
        select(AttendanceSession.id).where(AttendanceSession.subject_offering_id == offering_id)
    ).all()

    enrollments = db.scalars(
        select(StudentEnrollment).where(StudentEnrollment.subject_offering_id == offering_id)
    ).all()

    rows = []
    for enrollment in enrollments:
        student: Student = enrollment.student
        present = 0
        if session_ids:
            from sqlalchemy import func as sqlfunc
            present = db.scalar(
                select(sqlfunc.count(AttendanceRecord.id)).where(
                    AttendanceRecord.student_id == student.id,
                    AttendanceRecord.session_id.in_(session_ids),
                    AttendanceRecord.status == "present",
                )
            ) or 0
        total = len(session_ids)
        percentage = round((present / total) * 100, 2) if total else 0.0
        rows.append({
            "usn": student.usn,
            "name": student.name,
            "email": student.email,
            "section": student.section,
            "total_sessions": total,
            "present": present,
            "absent": total - present,
            "percentage": percentage,
        })

    csv_content = build_csv(
        rows,
        ["usn", "name", "email", "section", "total_sessions", "present", "absent", "percentage"],
    )
    filename = f"attendance_{offering.subject.subject_code}_{offering.section}.csv"
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
