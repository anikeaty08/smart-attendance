from datetime import UTC, datetime, date as dt_date

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, distinct, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    AcademicYear, AttendanceCorrection, AttendanceRecord,
    AttendanceSession, CondonationRequest, Department, Faculty, Holiday, LeaveRequest, SessionStatus,
    Student, StudentEnrollment, Subject, SubjectOffering,
    SubstituteAssignment, TimetableSlot,
)
from app.schemas import (
    AcademicYearCreate, AcademicYearOut, AcademicYearUpdate,
    CondonationRequestOut,
    CreateSubjectOfferingRequest, DepartmentCreate, DepartmentOut,
    DepartmentUpdate, FacultyOut, FacultyUpdate, HolidayCreate, HolidayOut,
    ImportResponse, LeaveRequestOut, StudentOut, StudentUpdate, SubjectCreate,
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
    h.active = False
    db.commit()
    return {"status": "deactivated"}


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


# ---------------------------------------------------------------------------
# Subjects CRUD
# ---------------------------------------------------------------------------

def _subject_out(s: Subject) -> dict:
    return {
        "id": s.id, "subject_code": s.subject_code, "subject_name": s.subject_name,
        "credits": s.credits, "semester": s.semester,
        "department_id": s.department_id,
        "department_code": s.department.code if s.department else None,
        "active": s.active,
    }


@router.get("/subjects")
def list_subjects(
    department_id: int | None = None, semester: int | None = None,
    search: str | None = None, page: int = 1, page_size: int = 50,
    current=Depends(require_role("admin")), db: Session = Depends(get_db),
):
    q = select(Subject)
    if department_id:
        q = q.where(Subject.department_id == department_id)
    if semester:
        q = q.where(Subject.semester == semester)
    if search:
        like = f"%{search}%"
        q = q.where(Subject.subject_code.ilike(like) | Subject.subject_name.ilike(like))
    result = paginate_query(db, q.order_by(Subject.semester, Subject.subject_code), page, page_size)
    return {**result, "items": [_subject_out(s) for s in result["items"]]}


@router.post("/subjects")
def create_subject(payload: SubjectCreate, current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    s = Subject(**payload.model_dump())
    db.add(s)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "subject_code_already_exists")
    db.refresh(s)
    return _subject_out(s)


@router.put("/subjects/{subject_id}")
def update_subject(subject_id: int, payload: SubjectUpdate, current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    s = db.get(Subject, subject_id)
    if not s:
        raise HTTPException(404, "subject_not_found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(s, k, v)
    db.commit()
    return _subject_out(s)


@router.delete("/subjects/{subject_id}")
def delete_subject(subject_id: int, current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    s = db.get(Subject, subject_id)
    if not s:
        raise HTTPException(404, "subject_not_found")
    s.active = False
    db.commit()
    return {"status": "deactivated"}


# ---------------------------------------------------------------------------
# Subject Offerings CRUD
# ---------------------------------------------------------------------------

def _offering_out(o: SubjectOffering) -> dict:
    enrolled = len(o.enrollments) if o.enrollments else 0
    return {
        "id": o.id, "subject_code": o.subject.subject_code, "subject_name": o.subject.subject_name,
        "faculty_name": o.faculty.name, "faculty_id": o.faculty_id,
        "academic_year": o.academic_year, "semester_type": o.semester_type,
        "section": o.section, "semester": o.semester,
        "branch_id": o.branch_id, "branch_code": o.branch.code if o.branch else None,
        "active": o.active, "enrollment_count": enrolled,
    }


@router.get("/subject-offerings")
def list_offerings(
    academic_year: str | None = None, branch_id: int | None = None,
    semester: int | None = None, section: str | None = None,
    faculty_id: int | None = None, page: int = 1, page_size: int = 50,
    current=Depends(require_role("admin")), db: Session = Depends(get_db),
):
    q = select(SubjectOffering)
    if academic_year:
        q = q.where(SubjectOffering.academic_year == academic_year)
    if branch_id:
        q = q.where(SubjectOffering.branch_id == branch_id)
    if semester:
        q = q.where(SubjectOffering.semester == semester)
    if section:
        q = q.where(SubjectOffering.section == section.upper())
    if faculty_id:
        q = q.where(SubjectOffering.faculty_id == faculty_id)
    result = paginate_query(db, q.order_by(SubjectOffering.semester, SubjectOffering.section), page, page_size)
    return {**result, "items": [_offering_out(o) for o in result["items"]]}


@router.post("/subject-offerings")
def create_offering(payload: CreateSubjectOfferingRequest, current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    if not db.get(Subject, payload.subject_id):
        raise HTTPException(400, "subject_not_found")
    if not db.get(Faculty, payload.faculty_id):
        raise HTTPException(400, "faculty_not_found")
    o = SubjectOffering(**payload.model_dump())
    db.add(o)
    db.commit()
    db.refresh(o)
    return _offering_out(o)


@router.put("/subject-offerings/{offering_id}")
def update_offering(offering_id: int, payload: UpdateSubjectOfferingRequest, current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    o = db.get(SubjectOffering, offering_id)
    if not o:
        raise HTTPException(404, "offering_not_found")
    for k, v in payload.model_dump(exclude_none=True).items():
        setattr(o, k, v)
    db.commit()
    return _offering_out(o)


@router.delete("/subject-offerings/{offering_id}")
def deactivate_offering(offering_id: int, current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    o = db.get(SubjectOffering, offering_id)
    if not o:
        raise HTTPException(404, "offering_not_found")
    o.active = False
    db.commit()
    return {"status": "deactivated"}


# ---------------------------------------------------------------------------
# Enrollments
# ---------------------------------------------------------------------------

@router.get("/enrollments")
def list_enrollments(
    offering_id: int | None = None, branch_id: int | None = None,
    page: int = 1, page_size: int = 50,
    current=Depends(require_role("admin")), db: Session = Depends(get_db),
):
    q = select(StudentEnrollment)
    if offering_id:
        q = q.where(StudentEnrollment.subject_offering_id == offering_id)
    if branch_id:
        q = q.join(Student, Student.id == StudentEnrollment.student_id).where(Student.branch_id == branch_id)
    result = paginate_query(db, q, page, page_size)
    return {
        **result,
        "items": [
            {
                "id": e.id, "student_id": e.student_id,
                "usn": e.student.usn, "student_name": e.student.name,
                "subject_offering_id": e.subject_offering_id,
                "subject_code": e.subject_offering.subject.subject_code,
                "subject_name": e.subject_offering.subject.subject_name,
                "enrollment_type": e.enrollment_type,
            }
            for e in result["items"]
        ],
    }


@router.delete("/enrollments/{enrollment_id}")
def delete_enrollment(enrollment_id: int, current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    e = db.get(StudentEnrollment, enrollment_id)
    if not e:
        raise HTTPException(404, "enrollment_not_found")
    db.delete(e)
    db.commit()
    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# CSV Imports with pre-validation
# ---------------------------------------------------------------------------

@router.post("/import/students", response_model=ImportResponse)
async def import_students(
    file: UploadFile = File(...),
    branch_code: str = "",
    batch_year: int = 2024,
    semester: int = 1,
    section: str = "A",
    current=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    rows = await parse_upload(file)
    errors = []
    valid = []

    # Resolve branch from code (can be overridden per row)
    default_branch = db.scalar(select(Department).where(Department.code == branch_code.upper())) if branch_code else None

    existing_emails = set(db.scalars(select(Student.email)).all())
    existing_usns = set(db.scalars(select(Student.usn)).all())
    file_emails: set = set()
    file_usns: set = set()

    for i, row in enumerate(rows, start=2):
        row_errors = []
        for field in ["usn", "name", "email"]:
            if not row.get(field):
                row_errors.append({"row": i, "field": field, "error": "required_field_missing"})

        if row_errors:
            errors.extend(row_errors)
            continue

        email = row["email"].strip().lower()
        usn = row["usn"].strip()

        if email in file_emails:
            errors.append({"row": i, "field": "email", "error": "duplicate_in_file"})
        elif email in existing_emails:
            errors.append({"row": i, "field": "email", "error": "already_exists_in_database"})
        else:
            file_emails.add(email)

        if usn in file_usns:
            errors.append({"row": i, "field": "usn", "error": "duplicate_in_file"})
        elif usn in existing_usns:
            errors.append({"row": i, "field": "usn", "error": "already_exists_in_database"})
        else:
            file_usns.add(usn)

        if errors:
            continue

        # Branch: prefer row value, fall back to query param
        row_branch_code = row.get("branch_code", "").strip().upper()
        branch = (
            db.scalar(select(Department).where(Department.code == row_branch_code))
            if row_branch_code else default_branch
        )

        valid.append(Student(
            usn=usn,
            name=row["name"].strip(),
            email=email,
            branch_id=branch.id if branch else None,
            batch_year=int(row.get("batch_year") or batch_year),
            current_semester=int(row.get("semester") or semester),
            section=(row.get("section") or section).upper(),
        ))

    if errors:
        return ImportResponse(imported=0, errors=errors)

    db.add_all(valid)
    db.commit()
    return ImportResponse(imported=len(valid), errors=[])


@router.post("/import/faculty", response_model=ImportResponse)
async def import_faculty(
    file: UploadFile = File(...),
    department_code: str = "",
    current=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    rows = await parse_upload(file)
    errors = []
    valid = []
    existing_emails = set(db.scalars(select(Faculty.email)).all())
    file_emails: set = set()
    default_dept = db.scalar(select(Department).where(Department.code == department_code.upper())) if department_code else None

    for i, row in enumerate(rows, start=2):
        for field in ["name", "email"]:
            if not row.get(field):
                errors.append({"row": i, "field": field, "error": "required_field_missing"})
        if errors:
            continue

        email = row["email"].strip().lower()
        if email in file_emails:
            errors.append({"row": i, "field": "email", "error": "duplicate_in_file"})
        elif email in existing_emails:
            errors.append({"row": i, "field": "email", "error": "already_exists_in_database"})
        else:
            file_emails.add(email)
            row_dept_code = row.get("department_code", "").strip().upper()
            dept = db.scalar(select(Department).where(Department.code == row_dept_code)) if row_dept_code else default_dept
            valid.append(Faculty(
                name=row["name"].strip(),
                email=email,
                department_id=dept.id if dept else None,
                is_hod=str(row.get("is_hod", "")).lower() == "true",
                is_admin=str(row.get("is_admin", "")).lower() == "true",
            ))

    if errors:
        return ImportResponse(imported=0, errors=errors)
    db.add_all(valid)
    db.commit()
    return ImportResponse(imported=len(valid), errors=[])


@router.post("/import/subjects", response_model=ImportResponse)
async def import_subjects(
    file: UploadFile = File(...),
    current=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    rows = await parse_upload(file)
    errors = []
    valid = []
    existing_codes = set(db.scalars(select(Subject.subject_code)).all())
    file_codes: set = set()

    for i, row in enumerate(rows, start=2):
        for field in ["subject_code", "subject_name", "semester"]:
            if not row.get(field):
                errors.append({"row": i, "field": field, "error": "required_field_missing"})
        if errors:
            continue

        code = row["subject_code"].strip().upper()
        if code in file_codes:
            errors.append({"row": i, "field": "subject_code", "error": "duplicate_in_file"})
        elif code in existing_codes:
            errors.append({"row": i, "field": "subject_code", "error": "already_exists_in_database"})
        else:
            file_codes.add(code)
            dept_code = row.get("department_code", "").strip().upper()
            dept = db.scalar(select(Department).where(Department.code == dept_code)) if dept_code else None
            valid.append(Subject(
                subject_code=code,
                subject_name=row["subject_name"].strip(),
                credits=int(row.get("credits") or 3),
                semester=int(row["semester"]),
                department_id=dept.id if dept else None,
            ))

    if errors:
        return ImportResponse(imported=0, errors=errors)
    db.add_all(valid)
    db.commit()
    return ImportResponse(imported=len(valid), errors=[])


@router.post("/import/enrollments", response_model=ImportResponse)
async def import_enrollments(
    file: UploadFile = File(...),
    academic_year: str = "",
    current=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    rows = await parse_upload(file)
    errors = []
    valid = []

    for i, row in enumerate(rows, start=2):
        usn = row.get("usn", "").strip()
        offering_id_raw = row.get("subject_offering_id", "").strip()
        if not usn or not offering_id_raw:
            errors.append({"row": i, "field": "usn/subject_offering_id", "error": "required_field_missing"})
            continue
        student = db.scalar(select(Student).where(Student.usn == usn))
        if not student:
            errors.append({"row": i, "field": "usn", "error": f"student_not_found: {usn}"})
            continue
        offering = db.get(SubjectOffering, int(offering_id_raw))
        if not offering:
            errors.append({"row": i, "field": "subject_offering_id", "error": f"offering_not_found: {offering_id_raw}"})
            continue
        valid.append(StudentEnrollment(
            student_id=student.id,
            subject_offering_id=offering.id,
            enrollment_type=row.get("enrollment_type") or "core",
        ))

    if errors:
        return ImportResponse(imported=0, errors=errors)
    try:
        db.add_all(valid)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "duplicate_enrollment_in_batch")
    return ImportResponse(imported=len(valid), errors=[])


# ---------------------------------------------------------------------------
# CSV Exports
# ---------------------------------------------------------------------------

@router.get("/export/students")
def export_students(
    branch_id: int | None = None, batch_year: int | None = None,
    semester: int | None = None, section: str | None = None,
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
    students = db.scalars(q.order_by(Student.usn)).all()
    rows = [
        {"usn": s.usn, "name": s.name, "email": s.email,
         "branch_code": s.branch.code if s.branch else "",
         "batch_year": s.batch_year, "semester": s.current_semester,
         "section": s.section, "status": s.status}
        for s in students
    ]
    csv_content = build_csv(rows, ["usn", "name", "email", "branch_code", "batch_year", "semester", "section", "status"])
    return StreamingResponse(iter([csv_content]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=students.csv"})


@router.get("/export/faculty")
def export_faculty(
    department_id: int | None = None,
    current=Depends(require_role("admin")), db: Session = Depends(get_db),
):
    q = select(Faculty)
    if department_id:
        q = q.where(Faculty.department_id == department_id)
    rows = [
        {"name": f.name, "email": f.email,
         "department": f.department.code if f.department else "",
         "is_hod": f.is_hod, "is_admin": f.is_admin, "status": f.status}
        for f in db.scalars(q.order_by(Faculty.name)).all()
    ]
    csv_content = build_csv(rows, ["name", "email", "department", "is_hod", "is_admin", "status"])
    return StreamingResponse(iter([csv_content]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=faculty.csv"})


@router.get("/export/subjects")
def export_subjects(
    department_id: int | None = None, semester: int | None = None,
    current=Depends(require_role("admin")), db: Session = Depends(get_db),
):
    q = select(Subject)
    if department_id:
        q = q.where(Subject.department_id == department_id)
    if semester:
        q = q.where(Subject.semester == semester)
    rows = [
        {"subject_code": s.subject_code, "subject_name": s.subject_name,
         "credits": s.credits, "semester": s.semester,
         "department": s.department.code if s.department else ""}
        for s in db.scalars(q.order_by(Subject.semester)).all()
    ]
    csv_content = build_csv(rows, ["subject_code", "subject_name", "credits", "semester", "department"])
    return StreamingResponse(iter([csv_content]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=subjects.csv"})


@router.get("/export/attendance")
def export_attendance(
    academic_year: str | None = None, branch_id: int | None = None,
    semester: int | None = None,
    current=Depends(require_role("admin")), db: Session = Depends(get_db),
):
    rows = _defaulters_query(db, threshold=101.0, academic_year=academic_year,
                              branch_id=branch_id, semester=semester)
    csv_content = build_csv(rows, ["usn", "student_name", "section", "subject_code",
                                    "subject_name", "total_sessions", "present_sessions", "percentage"])
    return StreamingResponse(iter([csv_content]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=attendance.csv"})


@router.get("/export/defaulters")
def export_defaulters(
    academic_year: str | None = None, branch_id: int | None = None,
    threshold: float = 75.0,
    current=Depends(require_role("admin")), db: Session = Depends(get_db),
):
    rows = _defaulters_query(db, threshold=threshold, academic_year=academic_year, branch_id=branch_id)
    csv_content = build_csv(rows, ["usn", "student_name", "section", "subject_code",
                                    "subject_name", "total_sessions", "present_sessions", "percentage"])
    return StreamingResponse(iter([csv_content]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=defaulters.csv"})


# ---------------------------------------------------------------------------
# Reports (optimized single-query aggregation)
# ---------------------------------------------------------------------------

def _defaulters_query(db: Session, threshold: float, academic_year: str | None = None,
                       branch_id: int | None = None, semester: int | None = None) -> list[dict]:
    q = select(
        Student.usn, Student.name.label("student_name"), Student.section,
        Subject.subject_code, Subject.subject_name,
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
    )
    if academic_year:
        q = q.where(SubjectOffering.academic_year == academic_year)
    if branch_id:
        q = q.where(SubjectOffering.branch_id == branch_id)
    if semester:
        q = q.where(SubjectOffering.semester == semester)
    q = q.group_by(Student.usn, Student.name, Student.section, Subject.subject_code, Subject.subject_name)
    q = q.having(func.count(distinct(AttendanceSession.id)) > 0)
    rows = db.execute(q).all()
    return [
        {
            "usn": r.usn, "student_name": r.student_name, "section": r.section,
            "subject_code": r.subject_code, "subject_name": r.subject_name,
            "total_sessions": r.total, "present_sessions": r.present,
            "percentage": round((r.present / r.total) * 100, 2),
        }
        for r in rows
        if (r.present / r.total) * 100 < threshold
    ]


@router.get("/reports/attendance")
def attendance_report(
    academic_year: str | None = None, branch_id: int | None = None,
    semester: int | None = None,
    current=Depends(require_role("admin")), db: Session = Depends(get_db),
):
    return _defaulters_query(db, threshold=101.0, academic_year=academic_year,
                              branch_id=branch_id, semester=semester)


@router.get("/reports/defaulters")
def defaulters_report(
    threshold: float = 75.0, academic_year: str | None = None,
    branch_id: int | None = None, semester: int | None = None,
    current=Depends(require_role("admin")), db: Session = Depends(get_db),
):
    return _defaulters_query(db, threshold=threshold, academic_year=academic_year,
                              branch_id=branch_id, semester=semester)


# ---------------------------------------------------------------------------
# Substitutes & corrections (admin can view all)
# ---------------------------------------------------------------------------

@router.get("/substitutes")
def list_all_substitutes(
    date_filter: str | None = None,
    current=Depends(require_role("admin")), db: Session = Depends(get_db),
):
    q = select(SubstituteAssignment)
    if date_filter:
        from datetime import date as dt
        q = q.where(SubstituteAssignment.date == dt.fromisoformat(date_filter))
    subs = db.scalars(q.order_by(SubstituteAssignment.date.desc())).all()
    return [
        {
            "id": s.id, "date": str(s.date),
            "subject_code": s.subject_offering.subject.subject_code,
            "original_faculty": s.original_faculty.name,
            "substitute_faculty": s.substitute_faculty.name if s.substitute_faculty else "cancelled",
            "reason": s.reason, "status": s.status,
        }
        for s in subs
    ]


@router.get("/corrections")
def list_all_corrections(
    page: int = 1,
    page_size: int = 50,
    current=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    result = paginate_query(db, select(AttendanceCorrection).order_by(AttendanceCorrection.corrected_at.desc()), page, page_size)
    return {
        **result,
        "items": [
            {
                "id": c.id, "session_id": c.session_id,
                "usn": c.student.usn, "student_name": c.student.name,
                "old_status": c.old_status, "new_status": c.new_status,
                "reason": c.reason, "corrected_by": c.corrector.name,
                "corrected_at": c.corrected_at,
            }
            for c in result["items"]
        ],
    }


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


@router.get("/leave-requests")
def list_leave_requests(
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
    current=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    query = select(LeaveRequest)
    if status:
        query = query.where(LeaveRequest.status == status)
    result = paginate_query(db, query.order_by(LeaveRequest.created_at.desc()), page, page_size)
    return {**result, "items": [_leave_out(r) for r in result["items"]]}


@router.get("/condonation-requests")
def list_condonation_requests(
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
    current=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    query = select(CondonationRequest)
    if status:
        query = query.where(CondonationRequest.status == status)
    result = paginate_query(db, query.order_by(CondonationRequest.created_at.desc()), page, page_size)
    return {**result, "items": [_condonation_out(r) for r in result["items"]]}


# ---------------------------------------------------------------------------
# Timetable upload (any department)
# ---------------------------------------------------------------------------

@router.post("/timetable/upload")
async def admin_upload_timetable(
    file: UploadFile = File(...),
    academic_year_id: int = 0,
    current=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    from datetime import time as dt_time
    rows = await parse_upload(file)
    errors = []
    slots = []
    valid_days = {"MON", "TUE", "WED", "THU", "FRI", "SAT"}

    for i, row in enumerate(rows, start=2):
        try:
            offering_id = int(row["subject_offering_id"])
            if not db.get(SubjectOffering, offering_id):
                errors.append({"row": i, "field": "subject_offering_id", "error": "offering_not_found"})
                continue
            day = row.get("day_of_week", "").upper()
            if day not in valid_days:
                errors.append({"row": i, "field": "day_of_week", "error": f"invalid_day: {day}"})
                continue
            start_p = row.get("start_time", "").split(":")
            end_p = row.get("end_time", "").split(":")
            slots.append(TimetableSlot(
                subject_offering_id=offering_id, day_of_week=day,
                slot_number=int(row.get("slot_number", 1)),
                start_time=dt_time(int(start_p[0]), int(start_p[1])),
                end_time=dt_time(int(end_p[0]), int(end_p[1])),
                room=row.get("room", ""),
                effective_from=dt_date.fromisoformat(row["effective_from"]),
                effective_until=dt_date.fromisoformat(row["effective_until"]) if row.get("effective_until") else None,
                academic_year_id=academic_year_id,
            ))
        except Exception as exc:
            errors.append({"row": i, "field": "unknown", "error": str(exc)})

    if errors:
        return {"imported": 0, "errors": errors}
    db.add_all(slots)
    db.commit()
    return {"imported": len(slots), "errors": []}
