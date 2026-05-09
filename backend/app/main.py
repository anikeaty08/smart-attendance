from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db
from app.models import (
    AccountStatus,
    AttendanceAttempt,
    AttendanceRecord,
    AttendanceSession,
    Faculty,
    SessionStatus,
    Student,
    StudentEnrollment,
    Subject,
    SubjectOffering,
)
from app.schemas import (
    ActiveSessionOut,
    AttendanceRecordOut,
    AttendanceSummaryOut,
    CreateSubjectOfferingRequest,
    GoogleLoginRequest,
    MarkAttendanceRequest,
    MarkAttendanceResponse,
    MeResponse,
    StartSessionRequest,
    StartSessionResponse,
    SubjectOfferingOut,
    TokenResponse,
)
from app.security import (
    create_access_token,
    find_user_by_email,
    hash_code,
    require_role,
    validate_allowed_domain,
    verify_code,
)
from app.utils import generate_session_code, haversine_meters

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Attendance System", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

admin_dir = Path(__file__).resolve().parents[2] / "admin-web"
if admin_dir.exists():
    app.mount("/admin/assets", StaticFiles(directory=admin_dir), name="admin-assets")


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def normalize_email(email: str) -> str:
    return email.strip().lower()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/admin", include_in_schema=False)
def admin_home():
    index = admin_dir / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="admin_web_not_found")
    return FileResponse(index)


@app.post("/auth/google", response_model=TokenResponse)
def google_login(payload: GoogleLoginRequest, db: Session = Depends(get_db)):
    email: str | None = None
    if settings.google_client_id and payload.id_token:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token

        try:
            claims = id_token.verify_oauth2_token(
                payload.id_token,
                google_requests.Request(),
                settings.google_client_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=401, detail="invalid_google_token") from exc
        if not claims.get("email_verified"):
            raise HTTPException(status_code=403, detail="google_email_not_verified")
        email = claims.get("email")
    elif payload.email:
        # Local MVP mode: accept email directly for development and demos.
        email = str(payload.email)
    else:
        raise HTTPException(status_code=400, detail="email_required_for_local_login")

    email = normalize_email(email)
    validate_allowed_domain(email)
    role, user = find_user_by_email(db, email)
    if not user or user.status != AccountStatus.active.value:
        raise HTTPException(status_code=403, detail="user_not_registered_or_inactive")
    token = create_access_token(user.email, role, user.id)
    return TokenResponse(access_token=token, role=role, email=user.email, name=user.name)


@app.get("/me", response_model=MeResponse)
def me(current=Depends(require_role("student", "faculty", "admin"))):
    user = current["user"]
    return MeResponse(
        id=user.id,
        role=current["role"],
        email=user.email,
        name=user.name,
        is_admin=bool(getattr(user, "is_admin", False)),
    )


def offering_out(offering: SubjectOffering, enrollment_type: str | None = None) -> SubjectOfferingOut:
    return SubjectOfferingOut(
        id=offering.id,
        subject_code=offering.subject.subject_code,
        subject_name=offering.subject.subject_name,
        faculty_name=offering.faculty.name,
        academic_year=offering.academic_year,
        semester_type=offering.semester_type,
        section=offering.section,
        semester=offering.semester,
        enrollment_type=enrollment_type,
    )


@app.get("/student/subjects", response_model=list[SubjectOfferingOut])
def student_subjects(current=Depends(require_role("student")), db: Session = Depends(get_db)):
    student: Student = current["user"]
    rows = db.execute(
        select(SubjectOffering, StudentEnrollment.enrollment_type)
        .join(StudentEnrollment, StudentEnrollment.subject_offering_id == SubjectOffering.id)
        .where(StudentEnrollment.student_id == student.id, SubjectOffering.active.is_(True))
        .order_by(SubjectOffering.semester, SubjectOffering.section)
    ).all()
    return [offering_out(offering, enrollment_type) for offering, enrollment_type in rows]


@app.get("/student/active-sessions", response_model=list[ActiveSessionOut])
def student_active_sessions(current=Depends(require_role("student")), db: Session = Depends(get_db)):
    student: Student = current["user"]
    now = utcnow()
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


def log_attempt(
    db: Session,
    request: Request,
    session_id: int | None,
    student_id: int | None,
    entered_code_valid: bool,
    location_valid: bool,
    distance: float | None,
    device_id: str | None,
    result: str,
    reason: str,
) -> None:
    db.add(
        AttendanceAttempt(
            session_id=session_id,
            student_id=student_id,
            entered_code_valid=entered_code_valid,
            location_valid=location_valid,
            distance_meters=distance,
            device_id=device_id,
            ip_address=request.client.host if request.client else None,
            result=result,
            reason=reason,
        )
    )
    db.commit()


@app.post("/student/attendance/mark", response_model=MarkAttendanceResponse)
def mark_attendance(
    payload: MarkAttendanceRequest,
    request: Request,
    current=Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    student: Student = current["user"]
    session = db.get(AttendanceSession, payload.session_id)
    now = utcnow()
    if not session:
        log_attempt(db, request, None, student.id, False, False, None, payload.device_id, "rejected", "session_not_found")
        raise HTTPException(status_code=404, detail="session_not_found")

    distance = haversine_meters(
        session.teacher_latitude,
        session.teacher_longitude,
        payload.student_latitude,
        payload.student_longitude,
    )
    code_ok = verify_code(payload.entered_code, session.code_hash)
    location_ok = distance <= session.radius_meters

    def reject(reason: str, status_code: int = 400):
        log_attempt(db, request, session.id, student.id, code_ok, location_ok, distance, payload.device_id, "rejected", reason)
        raise HTTPException(status_code=status_code, detail=reason)

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
    log_attempt(db, request, session.id, student.id, True, True, distance, payload.device_id, "accepted", "present")
    return MarkAttendanceResponse(status=record.status, distance_from_teacher=round(distance, 2), marked_at=record.marked_at)


@app.get("/student/attendance/history", response_model=list[AttendanceRecordOut])
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


@app.get("/student/attendance/summary", response_model=list[AttendanceSummaryOut])
def student_summary(current=Depends(require_role("student")), db: Session = Depends(get_db)):
    student: Student = current["user"]
    enrollments = db.scalars(select(StudentEnrollment).where(StudentEnrollment.student_id == student.id)).all()
    summaries: list[AttendanceSummaryOut] = []
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


@app.get("/faculty/offerings", response_model=list[SubjectOfferingOut])
def faculty_offerings(current=Depends(require_role("faculty", "admin")), db: Session = Depends(get_db)):
    faculty: Faculty = current["user"]
    rows = db.scalars(
        select(SubjectOffering).where(SubjectOffering.faculty_id == faculty.id, SubjectOffering.active.is_(True))
    ).all()
    return [offering_out(offering) for offering in rows]


@app.post("/faculty/sessions/start", response_model=StartSessionResponse)
def start_session(payload: StartSessionRequest, current=Depends(require_role("faculty", "admin")), db: Session = Depends(get_db)):
    faculty: Faculty = current["user"]
    offering = db.get(SubjectOffering, payload.subject_offering_id)
    if not offering or offering.faculty_id != faculty.id:
        raise HTTPException(status_code=403, detail="offering_not_assigned_to_faculty")
    radius = min(max(payload.radius_meters, settings.default_radius_meters), settings.max_radius_meters)
    duration = max(1, min(payload.duration_minutes, 30))
    code = generate_session_code()
    now = utcnow()
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
    return StartSessionResponse(id=session.id, code=code, starts_at=session.starts_at, ends_at=session.ends_at, radius_meters=radius)


@app.get("/faculty/sessions/{session_id}", response_model=ActiveSessionOut)
def get_faculty_session(session_id: int, current=Depends(require_role("faculty", "admin")), db: Session = Depends(get_db)):
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


@app.post("/faculty/sessions/{session_id}/end")
def end_session(session_id: int, current=Depends(require_role("faculty", "admin")), db: Session = Depends(get_db)):
    faculty: Faculty = current["user"]
    session = db.get(AttendanceSession, session_id)
    if not session or session.faculty_id != faculty.id:
        raise HTTPException(status_code=404, detail="session_not_found")
    session.status = SessionStatus.ended.value
    session.ends_at = min(as_utc(session.ends_at), utcnow())
    db.commit()
    return {"status": "ended", "session_id": session.id}


@app.get("/faculty/sessions/{session_id}/records", response_model=list[AttendanceRecordOut])
def session_records(session_id: int, current=Depends(require_role("faculty", "admin")), db: Session = Depends(get_db)):
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


async def parse_upload(file: UploadFile) -> list[dict[str, str]]:
    import io
    import pandas as pd

    content = await file.read()
    suffix = Path(file.filename or "").suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(io.BytesIO(content))
    else:
        df = pd.read_csv(io.BytesIO(content))
    df = df.fillna("")
    return [{str(k).strip(): str(v).strip() for k, v in row.items()} for row in df.to_dict(orient="records")]


@app.post("/admin/import/students")
async def import_students(file: UploadFile = File(...), current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    rows = await parse_upload(file)
    imported = 0
    for row in rows:
        email = normalize_email(row["email"])
        validate_allowed_domain(email)
        branch = db.scalar(select(Subject).where(Subject.subject_code == "__never__"))
        student = Student(
            usn=row["usn"],
            name=row["name"],
            email=email,
            current_semester=int(row.get("current_semester") or row.get("semester") or 1),
            branch_id=None if branch else None,
        )
        db.add(student)
        imported += 1
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="duplicate_or_invalid_student_import") from exc
    return {"imported": imported}


@app.post("/admin/import/faculty")
async def import_faculty(file: UploadFile = File(...), current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    rows = await parse_upload(file)
    for row in rows:
        email = normalize_email(row["email"])
        validate_allowed_domain(email)
        db.add(Faculty(name=row["name"], email=email, is_admin=str(row.get("is_admin", "")).lower() == "true"))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="duplicate_or_invalid_faculty_import") from exc
    return {"imported": len(rows)}


@app.post("/admin/import/subjects")
async def import_subjects(file: UploadFile = File(...), current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    rows = await parse_upload(file)
    for row in rows:
        db.add(
            Subject(
                subject_code=row["subject_code"],
                subject_name=row["subject_name"],
                credits=int(row.get("credits") or 3),
                semester=int(row.get("semester") or 1),
            )
        )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="duplicate_or_invalid_subject_import") from exc
    return {"imported": len(rows)}


@app.post("/admin/import/enrollments")
async def import_enrollments(file: UploadFile = File(...), current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    rows = await parse_upload(file)
    imported = 0
    for row in rows:
        student = db.scalar(select(Student).where(Student.usn == row["usn"]))
        offering = db.get(SubjectOffering, int(row["subject_offering_id"]))
        if not student or not offering:
            raise HTTPException(status_code=400, detail=f"invalid_enrollment_row:{row}")
        db.add(
            StudentEnrollment(
                student_id=student.id,
                subject_offering_id=offering.id,
                enrollment_type=row.get("enrollment_type") or "core",
            )
        )
        imported += 1
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="duplicate_or_invalid_enrollment_import") from exc
    return {"imported": imported}


@app.get("/admin/subject-offerings", response_model=list[SubjectOfferingOut])
def list_subject_offerings(current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    offerings = db.scalars(select(SubjectOffering).order_by(SubjectOffering.semester, SubjectOffering.section)).all()
    return [offering_out(offering) for offering in offerings]


@app.post("/admin/subject-offerings", response_model=SubjectOfferingOut)
def create_subject_offering(
    payload: CreateSubjectOfferingRequest,
    current=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    subject = db.get(Subject, payload.subject_id)
    faculty = db.get(Faculty, payload.faculty_id)
    if not subject:
        raise HTTPException(status_code=400, detail="subject_not_found")
    if not faculty:
        raise HTTPException(status_code=400, detail="faculty_not_found")
    offering = SubjectOffering(
        subject_id=payload.subject_id,
        faculty_id=payload.faculty_id,
        academic_year=payload.academic_year,
        semester_type=payload.semester_type,
        section=payload.section,
        branch_id=payload.branch_id,
        semester=payload.semester,
    )
    db.add(offering)
    db.commit()
    db.refresh(offering)
    return offering_out(offering)


@app.get("/admin/reports/attendance")
def attendance_report(current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    rows = db.execute(
        select(Subject.subject_code, Subject.subject_name, func.count(AttendanceRecord.id))
        .join(SubjectOffering, SubjectOffering.subject_id == Subject.id)
        .join(AttendanceSession, AttendanceSession.subject_offering_id == SubjectOffering.id)
        .join(AttendanceRecord, AttendanceRecord.session_id == AttendanceSession.id)
        .group_by(Subject.subject_code, Subject.subject_name)
    ).all()
    return [{"subject_code": code, "subject_name": name, "present_records": count} for code, name, count in rows]


@app.get("/admin/reports/defaulters")
def defaulters(threshold: float = 75.0, current=Depends(require_role("admin")), db: Session = Depends(get_db)):
    result = []
    enrollments = db.scalars(select(StudentEnrollment)).all()
    for enrollment in enrollments:
        sessions = db.scalars(
            select(AttendanceSession.id).where(AttendanceSession.subject_offering_id == enrollment.subject_offering_id)
        ).all()
        total = len(sessions)
        present = 0
        if total:
            present = db.scalar(
                select(func.count(AttendanceRecord.id)).where(
                    AttendanceRecord.student_id == enrollment.student_id,
                    AttendanceRecord.session_id.in_(sessions),
                    AttendanceRecord.status == "present",
                )
            ) or 0
        percentage = round((present / total) * 100, 2) if total else 0.0
        if total and percentage < threshold:
            result.append(
                {
                    "usn": enrollment.student.usn,
                    "student_name": enrollment.student.name,
                    "subject_code": enrollment.subject_offering.subject.subject_code,
                    "percentage": percentage,
                }
            )
    return result
