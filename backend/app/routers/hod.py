from datetime import UTC, datetime, date

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, distinct, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    AttendanceCorrection,
    AttendanceRecord,
    AttendanceSession,
    Faculty,
    SessionStatus,
    Student,
    StudentEnrollment,
    Subject,
    SubjectOffering,
    SubstituteAssignment,
    TimetableSlot,
)
from app.schemas import (
    AttendanceCorrectionOut,
    AttendanceCorrectionRequest,
    DefaulterOut,
    StudentListResponse,
    SubjectOfferingOut,
    SubstituteCreate,
    SubstituteOut,
    SubstituteUpdate,
    TimetableSlotCreate,
    TimetableSlotOut,
)
from app.security import require_role
from app.utils import build_csv, parse_upload

router = APIRouter(prefix="/hod", tags=["HOD"])


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _get_hod_dept(current: dict) -> int:
    """Extract department_id from HOD — raises if not set."""
    faculty: Faculty = current["user"]
    if not faculty.department_id:
        raise HTTPException(status_code=400, detail="hod_department_not_configured")
    return faculty.department_id


# ---------------------------------------------------------------------------
# Department overview
# ---------------------------------------------------------------------------

@router.get("/department")
def department_overview(current=Depends(require_role("hod")), db: Session = Depends(get_db)):
    dept_id = _get_hod_dept(current)

    total_students = db.scalar(select(func.count(Student.id)).where(Student.branch_id == dept_id)) or 0
    total_faculty = db.scalar(select(func.count(Faculty.id)).where(Faculty.department_id == dept_id)) or 0
    total_subjects = db.scalar(select(func.count(Subject.id)).where(Subject.department_id == dept_id)) or 0
    total_offerings = db.scalar(
        select(func.count(SubjectOffering.id)).where(
            SubjectOffering.branch_id == dept_id,
            SubjectOffering.active.is_(True),
        )
    ) or 0
    active_sessions = db.scalar(
        select(func.count(AttendanceSession.id))
        .join(SubjectOffering, SubjectOffering.id == AttendanceSession.subject_offering_id)
        .where(
            SubjectOffering.branch_id == dept_id,
            AttendanceSession.status == SessionStatus.active.value,
        )
    ) or 0

    return {
        "department_id": dept_id,
        "total_students": total_students,
        "total_faculty": total_faculty,
        "total_subjects": total_subjects,
        "total_offerings": total_offerings,
        "active_sessions": active_sessions,
    }


# ---------------------------------------------------------------------------
# Faculty in department
# ---------------------------------------------------------------------------

@router.get("/faculty")
def hod_faculty(current=Depends(require_role("hod")), db: Session = Depends(get_db)):
    dept_id = _get_hod_dept(current)
    faculty_list = db.scalars(
        select(Faculty).where(Faculty.department_id == dept_id, Faculty.status == "active")
    ).all()
    return [
        {
            "id": f.id,
            "name": f.name,
            "email": f.email,
            "is_hod": f.is_hod,
            "status": f.status,
        }
        for f in faculty_list
    ]


# ---------------------------------------------------------------------------
# Students in department — filterable by semester, batch_year, section, search
# ---------------------------------------------------------------------------

@router.get("/students")
def hod_students(
    batch_year: int | None = None,
    semester: int | None = None,
    section: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 50,
    current=Depends(require_role("hod")),
    db: Session = Depends(get_db),
):
    dept_id = _get_hod_dept(current)
    from app.utils import paginate_query

    query = select(Student).where(Student.branch_id == dept_id)
    if batch_year:
        query = query.where(Student.batch_year == batch_year)
    if semester:
        query = query.where(Student.current_semester == semester)
    if section:
        query = query.where(Student.section == section.upper())
    if search:
        like = f"%{search}%"
        query = query.where(
            Student.name.ilike(like) | Student.usn.ilike(like) | Student.email.ilike(like)
        )
    return paginate_query(db, query.order_by(Student.usn), page, page_size)


# ---------------------------------------------------------------------------
# Subject offerings in department
# ---------------------------------------------------------------------------

@router.get("/offerings")
def hod_offerings(
    academic_year: str | None = None,
    semester: int | None = None,
    section: str | None = None,
    current=Depends(require_role("hod")),
    db: Session = Depends(get_db),
):
    dept_id = _get_hod_dept(current)
    query = select(SubjectOffering).where(SubjectOffering.branch_id == dept_id)
    if academic_year:
        query = query.where(SubjectOffering.academic_year == academic_year)
    if semester:
        query = query.where(SubjectOffering.semester == semester)
    if section:
        query = query.where(SubjectOffering.section == section.upper())
    offerings = db.scalars(query.order_by(SubjectOffering.semester, SubjectOffering.section)).all()
    return [
        {
            "id": o.id,
            "subject_code": o.subject.subject_code,
            "subject_name": o.subject.subject_name,
            "faculty_name": o.faculty.name,
            "academic_year": o.academic_year,
            "semester": o.semester,
            "section": o.section,
            "active": o.active,
        }
        for o in offerings
    ]


# ---------------------------------------------------------------------------
# Timetable — view and upload
# ---------------------------------------------------------------------------

@router.get("/timetable", response_model=list[TimetableSlotOut])
def hod_timetable(
    academic_year_id: int | None = None,
    current=Depends(require_role("hod")),
    db: Session = Depends(get_db),
):
    dept_id = _get_hod_dept(current)
    offering_ids = db.scalars(
        select(SubjectOffering.id).where(SubjectOffering.branch_id == dept_id, SubjectOffering.active.is_(True))
    ).all()
    if not offering_ids:
        return []
    query = select(TimetableSlot).where(TimetableSlot.subject_offering_id.in_(offering_ids))
    if academic_year_id:
        query = query.where(TimetableSlot.academic_year_id == academic_year_id)
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


@router.post("/timetable/upload")
async def upload_timetable(
    file: UploadFile = File(...),
    academic_year_id: int = 0,
    current=Depends(require_role("hod")),
    db: Session = Depends(get_db),
):
    """Upload timetable CSV. Columns: subject_offering_id, day_of_week, slot_number,
    start_time (HH:MM), end_time (HH:MM), room, effective_from (YYYY-MM-DD)"""
    from datetime import time as dt_time
    dept_id = _get_hod_dept(current)
    rows = await parse_upload(file)
    errors = []
    slots = []

    valid_days = {"MON", "TUE", "WED", "THU", "FRI", "SAT"}
    for i, row in enumerate(rows, start=2):
        try:
            offering_id = int(row["subject_offering_id"])
            offering = db.get(SubjectOffering, offering_id)
            if not offering or offering.branch_id != dept_id:
                errors.append({"row": i, "field": "subject_offering_id", "error": "not_in_department"})
                continue
            day = row.get("day_of_week", "").upper()
            if day not in valid_days:
                errors.append({"row": i, "field": "day_of_week", "error": f"invalid_day: {day}"})
                continue
            start_parts = row.get("start_time", "").split(":")
            end_parts = row.get("end_time", "").split(":")
            start = dt_time(int(start_parts[0]), int(start_parts[1]))
            end = dt_time(int(end_parts[0]), int(end_parts[1]))
            slots.append(TimetableSlot(
                subject_offering_id=offering_id,
                day_of_week=day,
                slot_number=int(row.get("slot_number", 1)),
                start_time=start,
                end_time=end,
                room=row.get("room", ""),
                effective_from=date.fromisoformat(row["effective_from"]),
                effective_until=date.fromisoformat(row["effective_until"]) if row.get("effective_until") else None,
                academic_year_id=academic_year_id,
            ))
        except Exception as exc:
            errors.append({"row": i, "field": "unknown", "error": str(exc)})

    if errors:
        return {"imported": 0, "errors": errors}
    db.add_all(slots)
    db.commit()
    return {"imported": len(slots), "errors": []}


# ---------------------------------------------------------------------------
# Substitute assignments
# ---------------------------------------------------------------------------

@router.get("/substitutes", response_model=list[SubstituteOut])
def list_substitutes(
    date_filter: str | None = None,
    current=Depends(require_role("hod")),
    db: Session = Depends(get_db),
):
    dept_id = _get_hod_dept(current)
    query = (
        select(SubstituteAssignment)
        .join(SubjectOffering, SubjectOffering.id == SubstituteAssignment.subject_offering_id)
        .where(SubjectOffering.branch_id == dept_id)
    )
    if date_filter:
        query = query.where(SubstituteAssignment.date == date.fromisoformat(date_filter))
    subs = db.scalars(query.order_by(SubstituteAssignment.date.desc())).all()
    return [
        SubstituteOut(
            id=s.id,
            date=s.date,
            timetable_slot_id=s.timetable_slot_id,
            subject_offering_id=s.subject_offering_id,
            subject_code=s.subject_offering.subject.subject_code,
            original_faculty_name=s.original_faculty.name,
            substitute_faculty_name=s.substitute_faculty.name if s.substitute_faculty else None,
            reason=s.reason,
            status=s.status,
            assigned_by_name=s.assigned_by_faculty.name,
        )
        for s in subs
    ]


@router.post("/substitutes", response_model=SubstituteOut)
def create_substitute(
    payload: SubstituteCreate,
    current=Depends(require_role("hod")),
    db: Session = Depends(get_db),
):
    faculty: Faculty = current["user"]
    dept_id = _get_hod_dept(current)
    offering = db.get(SubjectOffering, payload.subject_offering_id)
    if not offering or offering.branch_id != dept_id:
        raise HTTPException(status_code=403, detail="offering_not_in_department")

    sub = SubstituteAssignment(
        date=payload.date,
        timetable_slot_id=payload.timetable_slot_id,
        subject_offering_id=payload.subject_offering_id,
        original_faculty_id=payload.original_faculty_id,
        substitute_faculty_id=payload.substitute_faculty_id,
        reason=payload.reason,
        assigned_by=faculty.id,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return SubstituteOut(
        id=sub.id,
        date=sub.date,
        timetable_slot_id=sub.timetable_slot_id,
        subject_offering_id=sub.subject_offering_id,
        subject_code=sub.subject_offering.subject.subject_code,
        original_faculty_name=sub.original_faculty.name,
        substitute_faculty_name=sub.substitute_faculty.name if sub.substitute_faculty else None,
        reason=sub.reason,
        status=sub.status,
        assigned_by_name=faculty.name,
    )


@router.put("/substitutes/{sub_id}")
def update_substitute(
    sub_id: int,
    payload: SubstituteUpdate,
    current=Depends(require_role("hod")),
    db: Session = Depends(get_db),
):
    dept_id = _get_hod_dept(current)
    sub = db.get(SubstituteAssignment, sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="substitute_not_found")
    if sub.subject_offering.branch_id != dept_id:
        raise HTTPException(status_code=403, detail="access_denied")
    if payload.substitute_faculty_id is not None:
        sub.substitute_faculty_id = payload.substitute_faculty_id
    if payload.status is not None:
        sub.status = payload.status
    db.commit()
    return {"status": "updated"}


# ---------------------------------------------------------------------------
# Attendance corrections (view all in dept — no 48h restriction for HOD)
# ---------------------------------------------------------------------------

@router.get("/corrections", response_model=list[AttendanceCorrectionOut])
def hod_corrections(
    current=Depends(require_role("hod")),
    db: Session = Depends(get_db),
):
    dept_id = _get_hod_dept(current)
    corrections = db.scalars(
        select(AttendanceCorrection)
        .join(AttendanceSession, AttendanceSession.id == AttendanceCorrection.session_id)
        .join(SubjectOffering, SubjectOffering.id == AttendanceSession.subject_offering_id)
        .where(SubjectOffering.branch_id == dept_id)
        .order_by(AttendanceCorrection.corrected_at.desc())
    ).all()
    return [
        AttendanceCorrectionOut(
            id=c.id,
            record_id=c.record_id,
            session_id=c.session_id,
            student_id=c.student_id,
            student_name=c.student.name,
            usn=c.student.usn,
            old_status=c.old_status,
            new_status=c.new_status,
            reason=c.reason,
            corrected_by_name=c.corrector.name,
            corrected_at=c.corrected_at,
        )
        for c in corrections
    ]


# ---------------------------------------------------------------------------
# Attendance report for department
# ---------------------------------------------------------------------------

@router.get("/attendance/report")
def hod_report(
    academic_year: str | None = None,
    semester: int | None = None,
    section: str | None = None,
    current=Depends(require_role("hod")),
    db: Session = Depends(get_db),
):
    dept_id = _get_hod_dept(current)
    query = select(
        Student.usn,
        Student.name,
        Student.section,
        Subject.subject_code,
        Subject.subject_name,
        func.count(distinct(AttendanceSession.id)).label("total"),
        func.count(distinct(AttendanceRecord.id)).label("present"),
    ).select_from(StudentEnrollment).join(
        Student, Student.id == StudentEnrollment.student_id
    ).join(
        SubjectOffering, SubjectOffering.id == StudentEnrollment.subject_offering_id
    ).join(
        Subject, Subject.id == SubjectOffering.subject_id
    ).outerjoin(
        AttendanceSession, AttendanceSession.subject_offering_id == SubjectOffering.id
    ).outerjoin(
        AttendanceRecord,
        and_(
            AttendanceRecord.session_id == AttendanceSession.id,
            AttendanceRecord.student_id == Student.id,
            AttendanceRecord.status == "present",
        ),
    ).where(SubjectOffering.branch_id == dept_id)

    if academic_year:
        query = query.where(SubjectOffering.academic_year == academic_year)
    if semester:
        query = query.where(SubjectOffering.semester == semester)
    if section:
        query = query.where(SubjectOffering.section == section.upper())

    query = query.group_by(Student.usn, Student.name, Student.section, Subject.subject_code, Subject.subject_name)
    rows = db.execute(query).all()

    return [
        {
            "usn": r.usn,
            "name": r.name,
            "section": r.section,
            "subject_code": r.subject_code,
            "subject_name": r.subject_name,
            "total_sessions": r.total,
            "present": r.present,
            "percentage": round((r.present / r.total) * 100, 2) if r.total else 0.0,
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Defaulters report
# ---------------------------------------------------------------------------

@router.get("/defaulters")
def hod_defaulters(
    threshold: float = 75.0,
    academic_year: str | None = None,
    semester: int | None = None,
    current=Depends(require_role("hod")),
    db: Session = Depends(get_db),
):
    dept_id = _get_hod_dept(current)
    query = select(
        Student.usn,
        Student.name,
        Student.section,
        Subject.subject_code,
        Subject.subject_name,
        func.count(distinct(AttendanceSession.id)).label("total"),
        func.count(distinct(AttendanceRecord.id)).label("present"),
    ).select_from(StudentEnrollment).join(
        Student, Student.id == StudentEnrollment.student_id
    ).join(
        SubjectOffering, SubjectOffering.id == StudentEnrollment.subject_offering_id
    ).join(
        Subject, Subject.id == SubjectOffering.subject_id
    ).outerjoin(
        AttendanceSession, AttendanceSession.subject_offering_id == SubjectOffering.id
    ).outerjoin(
        AttendanceRecord,
        and_(
            AttendanceRecord.session_id == AttendanceSession.id,
            AttendanceRecord.student_id == Student.id,
            AttendanceRecord.status == "present",
        ),
    ).where(SubjectOffering.branch_id == dept_id)

    if academic_year:
        query = query.where(SubjectOffering.academic_year == academic_year)
    if semester:
        query = query.where(SubjectOffering.semester == semester)

    query = query.group_by(
        Student.usn, Student.name, Student.section, Subject.subject_code, Subject.subject_name
    ).having(func.count(distinct(AttendanceSession.id)) > 0)

    rows = db.execute(query).all()
    return [
        {
            "usn": r.usn,
            "name": r.name,
            "section": r.section,
            "subject_code": r.subject_code,
            "subject_name": r.subject_name,
            "total_sessions": r.total,
            "present": r.present,
            "percentage": round((r.present / r.total) * 100, 2),
        }
        for r in rows
        if r.total and (r.present / r.total) * 100 < threshold
    ]


# ---------------------------------------------------------------------------
# Export attendance CSV
# ---------------------------------------------------------------------------

@router.get("/export/attendance")
def export_attendance(
    academic_year: str | None = None,
    semester: int | None = None,
    section: str | None = None,
    current=Depends(require_role("hod")),
    db: Session = Depends(get_db),
):
    dept_id = _get_hod_dept(current)
    data = hod_report(academic_year=academic_year, semester=semester, section=section, current=current, db=db)
    csv_content = build_csv(
        data,
        ["usn", "name", "section", "subject_code", "subject_name", "total_sessions", "present", "percentage"],
    )
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=dept_attendance.csv"},
    )


@router.get("/export/defaulters")
def export_defaulters(
    threshold: float = 75.0,
    academic_year: str | None = None,
    semester: int | None = None,
    current=Depends(require_role("hod")),
    db: Session = Depends(get_db),
):
    data = hod_defaulters(threshold=threshold, academic_year=academic_year, semester=semester, current=current, db=db)
    csv_content = build_csv(
        data,
        ["usn", "name", "section", "subject_code", "subject_name", "total_sessions", "present", "percentage"],
    )
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=defaulters.csv"},
    )
