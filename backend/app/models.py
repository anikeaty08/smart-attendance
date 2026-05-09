from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, Time, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AccountStatus(str, Enum):
    active = "active"
    inactive = "inactive"


class SessionStatus(str, Enum):
    active = "active"
    ended = "ended"
    expired = "expired"


class AttendanceStatus(str, Enum):
    present = "present"
    absent = "absent"
    late = "late"
    manual_present = "manual_present"
    excused = "excused"
    rejected = "rejected"


class LeaveType(str, Enum):
    medical = "medical"
    od = "od"
    personal = "personal"


class RequestStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class SubstituteStatus(str, Enum):
    assigned = "assigned"
    completed = "completed"
    cancelled = "cancelled"


# ---------------------------------------------------------------------------
# Core tables
# ---------------------------------------------------------------------------

class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    usn: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    batch_year: Mapped[int] = mapped_column(Integer, default=2024)
    current_semester: Mapped[int] = mapped_column(Integer)
    section: Mapped[str] = mapped_column(String(10), default="A")
    status: Mapped[str] = mapped_column(String(20), default=AccountStatus.active.value)

    branch = relationship("Department")
    enrollments = relationship("StudentEnrollment", back_populates="student")


class Faculty(Base):
    __tablename__ = "faculty"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=AccountStatus.active.value)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_hod: Mapped[bool] = mapped_column(Boolean, default=False)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    department = relationship("Department")


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    subject_name: Mapped[str] = mapped_column(String(180))
    credits: Mapped[int] = mapped_column(Integer, default=3)
    semester: Mapped[int] = mapped_column(Integer)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)

    department = relationship("Department")


# ---------------------------------------------------------------------------
# Academic year & calendar
# ---------------------------------------------------------------------------

class AcademicYear(Base):
    __tablename__ = "academic_years"

    id: Mapped[int] = mapped_column(primary_key=True)
    year_code: Mapped[str] = mapped_column(String(20), unique=True)
    start_date: Mapped[datetime] = mapped_column(Date)
    end_date: Mapped[datetime] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Holiday(Base):
    __tablename__ = "holidays"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime] = mapped_column(Date, unique=True)
    name: Mapped[str] = mapped_column(String(120))
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_years.id"), index=True)

    academic_year = relationship("AcademicYear")


# ---------------------------------------------------------------------------
# Offerings & enrollments
# ---------------------------------------------------------------------------

class SubjectOffering(Base):
    __tablename__ = "subject_offerings"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id"), index=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id"), index=True)
    academic_year: Mapped[str] = mapped_column(String(20))
    semester_type: Mapped[str] = mapped_column(String(20))
    section: Mapped[str] = mapped_column(String(30), default="A")
    branch_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    semester: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    subject = relationship("Subject")
    faculty = relationship("Faculty")
    branch = relationship("Department")
    enrollments = relationship("StudentEnrollment", back_populates="subject_offering")


class StudentEnrollment(Base):
    __tablename__ = "student_enrollments"
    __table_args__ = (UniqueConstraint("student_id", "subject_offering_id", name="uq_student_offering"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    subject_offering_id: Mapped[int] = mapped_column(ForeignKey("subject_offerings.id"), index=True)
    enrollment_type: Mapped[str] = mapped_column(String(40), default="core")

    student = relationship("Student", back_populates="enrollments")
    subject_offering = relationship("SubjectOffering", back_populates="enrollments")


# ---------------------------------------------------------------------------
# Timetable
# ---------------------------------------------------------------------------

class TimetableSlot(Base):
    __tablename__ = "timetable_slots"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_offering_id: Mapped[int] = mapped_column(ForeignKey("subject_offerings.id"), index=True)
    day_of_week: Mapped[str] = mapped_column(String(3))
    slot_number: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[datetime] = mapped_column(Time)
    end_time: Mapped[datetime] = mapped_column(Time)
    room: Mapped[str] = mapped_column(String(40), default="")
    effective_from: Mapped[datetime] = mapped_column(Date)
    effective_until: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_years.id"), index=True)

    subject_offering = relationship("SubjectOffering")
    academic_year = relationship("AcademicYear")


# ---------------------------------------------------------------------------
# Substitute handling
# ---------------------------------------------------------------------------

class SubstituteAssignment(Base):
    __tablename__ = "substitute_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime] = mapped_column(Date, index=True)
    timetable_slot_id: Mapped[int | None] = mapped_column(ForeignKey("timetable_slots.id"), nullable=True)
    subject_offering_id: Mapped[int] = mapped_column(ForeignKey("subject_offerings.id"), index=True)
    original_faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id"), index=True)
    substitute_faculty_id: Mapped[int | None] = mapped_column(ForeignKey("faculty.id"), nullable=True)
    reason: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(20), default=SubstituteStatus.assigned.value)
    assigned_by: Mapped[int] = mapped_column(ForeignKey("faculty.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    timetable_slot = relationship("TimetableSlot")
    subject_offering = relationship("SubjectOffering")
    original_faculty = relationship("Faculty", foreign_keys=[original_faculty_id])
    substitute_faculty = relationship("Faculty", foreign_keys=[substitute_faculty_id])
    assigned_by_faculty = relationship("Faculty", foreign_keys=[assigned_by])


# ---------------------------------------------------------------------------
# Attendance
# ---------------------------------------------------------------------------

class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_offering_id: Mapped[int] = mapped_column(ForeignKey("subject_offerings.id"), index=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id"), index=True)
    session_type: Mapped[str] = mapped_column(String(30), default="lecture")
    code_hash: Mapped[str] = mapped_column(String(255))
    teacher_latitude: Mapped[float] = mapped_column(Float)
    teacher_longitude: Mapped[float] = mapped_column(Float)
    radius_meters: Mapped[int] = mapped_column(Integer, default=10)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default=SessionStatus.active.value, index=True)

    subject_offering = relationship("SubjectOffering")
    faculty = relationship("Faculty")
    records = relationship("AttendanceRecord", back_populates="session")


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (UniqueConstraint("session_id", "student_id", name="uq_session_student"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("attendance_sessions.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default=AttendanceStatus.present.value)
    student_latitude: Mapped[float] = mapped_column(Float)
    student_longitude: Mapped[float] = mapped_column(Float)
    gps_accuracy_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_from_teacher: Mapped[float] = mapped_column(Float)
    marked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    verification_method: Mapped[str] = mapped_column(String(40), default="code_location")
    device_id: Mapped[str | None] = mapped_column(String(120), nullable=True)

    session = relationship("AttendanceSession", back_populates="records")
    student = relationship("Student")


class AttendanceAttempt(Base):
    __tablename__ = "attendance_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("attendance_sessions.id"), nullable=True, index=True)
    student_id: Mapped[int | None] = mapped_column(ForeignKey("students.id"), nullable=True, index=True)
    entered_code_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    location_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    distance_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    device_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(80), nullable=True)
    result: Mapped[str] = mapped_column(String(80))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Attendance corrections (audit trail)
# ---------------------------------------------------------------------------

class AttendanceCorrection(Base):
    __tablename__ = "attendance_corrections"

    id: Mapped[int] = mapped_column(primary_key=True)
    record_id: Mapped[int | None] = mapped_column(ForeignKey("attendance_records.id"), nullable=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("attendance_sessions.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    old_status: Mapped[str] = mapped_column(String(30))
    new_status: Mapped[str] = mapped_column(String(30))
    reason: Mapped[str] = mapped_column(Text)
    corrected_by: Mapped[int] = mapped_column(ForeignKey("faculty.id"))
    corrected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    record = relationship("AttendanceRecord")
    session = relationship("AttendanceSession")
    student = relationship("Student")
    corrector = relationship("Faculty")


# ---------------------------------------------------------------------------
# Leave / OD requests (schema ready, UI later)
# ---------------------------------------------------------------------------

class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    leave_type: Mapped[str] = mapped_column(String(20), default=LeaveType.medical.value)
    start_date: Mapped[datetime] = mapped_column(Date)
    end_date: Mapped[datetime] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(Text, default="")
    document_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=RequestStatus.pending.value)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("faculty.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    student = relationship("Student")
    reviewer = relationship("Faculty")


class CondonationRequest(Base):
    __tablename__ = "condonation_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    subject_offering_id: Mapped[int] = mapped_column(ForeignKey("subject_offerings.id"), index=True)
    current_percentage: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default=RequestStatus.pending.value)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("faculty.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    student = relationship("Student")
    subject_offering = relationship("SubjectOffering")
    reviewer = relationship("Faculty")
