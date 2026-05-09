from datetime import UTC, datetime, date as dt_date

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, distinct, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    AcademicYear, AttendanceCorrection, AttendanceRecord,
    AttendanceSession, Department, Faculty, Holiday, SessionStatus,
    Student, StudentEnrollment, Subject, SubjectOffering,
    SubstituteAssignment, TimetableSlot,
)
from app.schemas import (
    AcademicYearCreate, AcademicYearOut, AcademicYearUpdate,
    CreateSubjectOfferingRequest, DepartmentCreate, DepartmentOut,
    DepartmentUpdate, FacultyOut, FacultyUpdate, HolidayCreate, HolidayOut,
    ImportResponse, StudentOut, StudentUpdate, SubjectCreate,
    SubjectOfferingOut, SubjectOut, SubjectUpdate, UpdateSubjectOfferingRequest,
)
from app.security import require_role
from app.utils import build_csv, paginate_query, parse_upload

router = APIRouter(prefix="/admin", tags=["Admin"])


def _utcnow() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Dashboard metrics
# ---------------------------------------------------------------------------

@router.get("/dashboard")
def dashboard(current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    return {
        "total_students": db.scalar(select(func.count(Student.id))) or 0,
        "total_faculty": db.scalar(select(func.count(Faculty.id))) or 0,
        "total_departments": db.scalar(select(func.count(Department.id))) or 0,
        "total_subjects": db.scalar(select(func.count(Subject.id))) or 0,
        "total_offerings": db.scalar(select(func.count(SubjectOffering.id))) or 0,
        "total_sessions": db.scalar(select(func.count(AttendanceSession.id))) or 0,
        "active_sessions": db.scalar(
            select(func.count(AttendanceSession.id)).where(
                AttendanceSession.status == SessionStatus.active.value
            )
        ) or 0,
        "total_attendance_records": db.scalar(select(func.count(AttendanceRecord.id))) or 0,
    }


# ---------------------------------------------------------------------------
# Academic Years
# ---------------------------------------------------------------------------

@router.get("/academic-years", response_model=list[AcademicYearOut])
def list_academic_years(current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    return db.scalars(select(AcademicYear).order_by(AcademicYear.year_code.desc())).all()


@router.post("/academic-years", response_model=AcademicYearOut)
def create_academic_year(payload: AcademicYearCreate, current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    if payload.is_current:
        db.execute(AcademicYear.__table__.update().values(is_current=False))
    ay = AcademicYear(**payload.model_dump())
    db.add(ay)
    db.commit()
    db.refresh(ay)
    return ay


@router.put("/academic-years/{ay_id}", response_model=AcademicYearOut)
def update_academic_year(ay_id: int, payload: AcademicYearUpdate, current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    ay = db.get(AcademicYear, ay_id)
    if not ay:
        raise HTTPException(404, "academic_year_not_found")
    if payload.is_current:
        db.execute(AcademicYear.__table__.update().values(is_current=False))
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(ay, k, v)
    db.commit()
    db.refresh(ay)
    return ay


# ---------------------------------------------------------------------------
# Holidays
# ---------------------------------------------------------------------------

@router.get("/holidays", response_model=list[HolidayOut])
def list_holidays(academic_year_id: int | None = None, current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    q = select(Holiday)
    if academic_year_id:
        q = q.where(Holiday.academic_year_id == academic_year_id)
    return db.scalars(q.order_by(Holiday.date)).all()


@router.post("/holidays", response_model=HolidayOut)
def create_holiday(payload: HolidayCreate, current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    h = Holiday(**payload.model_dump())
    db.add(h)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "holiday_date_already_exists")
    db.refresh(h)
    return h


@router.delete("/holidays/{h_id}")
def delete_holiday(h_id: int, current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    h = db.get(Holiday, h_id)
    if not h:
        raise HTTPException(404, "holiday_not_found")
    db.delete(h)
    db.commit()
    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# Departments
# ---------------------------------------------------------------------------

@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    return db.scalars(select(Department).order_by(Department.code)).all()


@router.post("/departments", response_model=DepartmentOut)
def create_department(payload: DepartmentCreate, current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    dept = Department(**payload.model_dump())
    db.add(dept)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "department_code_or_name_exists")
    db.refresh(dept)
    return dept


@router.put("/departments/{dept_id}", response_model=DepartmentOut)
def update_department(dept_id: int, payload: DepartmentUpdate, current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    dept = db.get(Department, dept_id)
    if not dept:
        raise HTTPException(404, "department_not_found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(dept, k, v)
    db.commit()
    db.refresh(dept)
    return dept


# ---------------------------------------------------------------------------
# Students CRUD
# ---------------------------------------------------------------------------

def _student_out(s: Student) -> dict:
    return {
        "id": s.id, "usn": s.usn, "name": s.name, "email": s.email,
        "branch_id": s.branch_id,
        "branch_code": s.branch.code if s.branch else None,
        "branch_name": s.branch.name if s.branch else None,
        "batch_year": s.batch_year, "current_semester": s.current_semester,
        "section": s.section, "status": s.status,
    }


@router.get("/students")
def list_students(
    branch_id: int | None = None, batch_year: int | None = None,
    semester: int | None = None, section: str | None = None,
    search: str | None = None, page: int = 1, page_size: int = 50,
    current=Depends(require_role("admin")), db: Session = Depends(get_db),
):
    q = select(Student)
    if branch_id:
        q = q.where(Student.branch_id == branch_id)
    if batch_year:
        q = q.where(Student.batch_year == batch_year)
    if semester:
        q = q.where(Student.current_semester == semester)
    if section:
        q = q.where(Student.section == section.upper())
    if search:
        like = f"%{search}%"
        q = q.where(Student.name.ilike(like) | Student.usn.ilike(like) | Student.email.ilike(like))
    result = paginate_query(db, q.order_by(Student.usn), page, page_size)
    return {**result, "items": [_student_out(s) for s in result["items"]]}


@router.get("/students/{student_id}")
def get_student(student_id: int, current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    s = db.get(Student, student_id)
    if not s:
        raise HTTPException(404, "student_not_found")
    return _student_out(s)


@router.put("/students/{student_id}")
def update_student(student_id: int, payload: StudentUpdate, current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    s = db.get(Student, student_id)
    if not s:
        raise HTTPException(404, "student_not_found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(s, k, v)
    db.commit()
    return _student_out(s)


@router.delete("/students/{student_id}")
def deactivate_student(student_id: int, current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    s = db.get(Student, student_id)
    if not s:
        raise HTTPException(404, "student_not_found")
    s.status = "inactive"
    db.commit()
    return {"status": "deactivated"}


# ---------------------------------------------------------------------------
# Faculty CRUD
# ---------------------------------------------------------------------------

def _faculty_out(f: Faculty) -> dict:
    return {
        "id": f.id, "name": f.name, "email": f.email,
        "department_id": f.department_id,
        "department_code": f.department.code if f.department else None,
        "department_name": f.department.name if f.department else None,
        "status": f.status, "is_admin": f.is_admin, "is_hod": f.is_hod,
    }


@router.get("/faculty")
def list_faculty(
    department_id: int | None = None, search: str | None = None,
    page: int = 1, page_size: int = 50,
    current=Depends(require_role("admin")), db: Session = Depends(get_db),
):
    q = select(Faculty)
    if department_id:
        q = q.where(Faculty.department_id == department_id)
    if search:
        like = f"%{search}%"
        q = q.where(Faculty.name.ilike(like) | Faculty.email.ilike(like))
    result = paginate_query(db, q.order_by(Faculty.name), page, page_size)
    return {**result, "items": [_faculty_out(f) for f in result["items"]]}


@router.get("/faculty/{faculty_id}")
def get_faculty(faculty_id: int, current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    f = db.get(Faculty, faculty_id)
    if not f:
        raise HTTPException(404, "faculty_not_found")
    return _faculty_out(f)


@router.put("/faculty/{faculty_id}")
def update_faculty(faculty_id: int, payload: FacultyUpdate, current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    f = db.get(Faculty, faculty_id)
    if not f:
        raise HTTPException(404, "faculty_not_found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(f, k, v)
    db.commit()
    return _faculty_out(f)


@router.delete("/faculty/{faculty_id}")
def deactivate_faculty(faculty_id: int, current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    f = db.get(Faculty, faculty_id)
    if not f:
        raise HTTPException(404, "faculty_not_found")
    f.status = "inactive"
    db.commit()
    return {"status": "deactivated"}
