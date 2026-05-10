from datetime import date, datetime, time

from pydantic import BaseModel, EmailStr, Field


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class GoogleLoginRequest(BaseModel):
    id_token: str | None = None
    email: EmailStr | None = None


class WebLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    email: EmailStr
    name: str


class MeResponse(BaseModel):
    id: int
    role: str
    email: EmailStr
    name: str
    is_admin: bool = False
    is_hod: bool = False
    department_id: int | None = None
    department_name: str | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=4)
    new_password: str = Field(min_length=4)


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class PaginationMeta(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int


# ---------------------------------------------------------------------------
# Academic Year
# ---------------------------------------------------------------------------

class AcademicYearOut(BaseModel):
    id: int
    year_code: str
    start_date: date
    end_date: date
    is_current: bool
    active: bool = True


class AcademicYearCreate(BaseModel):
    year_code: str
    start_date: date
    end_date: date
    is_current: bool = False


class AcademicYearUpdate(BaseModel):
    year_code: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_current: bool | None = None
    active: bool | None = None


# ---------------------------------------------------------------------------
# Holiday
# ---------------------------------------------------------------------------

class HolidayOut(BaseModel):
    id: int
    date: date
    name: str
    academic_year_id: int
    active: bool = True


class HolidayCreate(BaseModel):
    date: date
    name: str
    academic_year_id: int


# ---------------------------------------------------------------------------
# Department
# ---------------------------------------------------------------------------

class DepartmentOut(BaseModel):
    id: int
    name: str
    code: str


class DepartmentCreate(BaseModel):
    name: str
    code: str


class DepartmentUpdate(BaseModel):
    name: str | None = None
    code: str | None = None


# ---------------------------------------------------------------------------
# Student
# ---------------------------------------------------------------------------

class StudentOut(BaseModel):
    id: int
    usn: str
    name: str
    email: EmailStr
    branch_id: int | None = None
    branch_code: str | None = None
    branch_name: str | None = None
    batch_year: int
    current_semester: int
    section: str
    status: str


class StudentUpdate(BaseModel):
    name: str | None = None
    branch_id: int | None = None
    batch_year: int | None = None
    current_semester: int | None = None
    section: str | None = None
    status: str | None = None


class StudentListResponse(BaseModel):
    items: list[StudentOut]
    pagination: PaginationMeta


# ---------------------------------------------------------------------------
# Faculty
# ---------------------------------------------------------------------------

class FacultyOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    department_id: int | None = None
    department_code: str | None = None
    department_name: str | None = None
    status: str
    is_admin: bool
    is_hod: bool


class FacultyUpdate(BaseModel):
    name: str | None = None
    department_id: int | None = None
    status: str | None = None
    is_admin: bool | None = None
    is_hod: bool | None = None


class FacultyListResponse(BaseModel):
    items: list[FacultyOut]
    pagination: PaginationMeta


class SetPasswordRequest(BaseModel):
    password: str = Field(min_length=4)


# ---------------------------------------------------------------------------
# Subject
# ---------------------------------------------------------------------------

class SubjectOut(BaseModel):
    id: int
    subject_code: str
    subject_name: str
    credits: int
    semester: int
    department_id: int | None = None
    department_code: str | None = None
    active: bool = True


class SubjectCreate(BaseModel):
    subject_code: str
    subject_name: str
    credits: int = 3
    semester: int
    department_id: int | None = None


class SubjectUpdate(BaseModel):
    subject_code: str | None = None
    subject_name: str | None = None
    credits: int | None = None
    semester: int | None = None
    department_id: int | None = None
    active: bool | None = None


class SubjectListResponse(BaseModel):
    items: list[SubjectOut]
    pagination: PaginationMeta


# ---------------------------------------------------------------------------
# Subject Offering
# ---------------------------------------------------------------------------

class SubjectOfferingOut(BaseModel):
    id: int
    subject_code: str
    subject_name: str
    faculty_name: str
    faculty_id: int
    academic_year: str
    semester_type: str
    section: str
    semester: int
    branch_id: int | None = None
    branch_code: str | None = None
    active: bool = True
    enrollment_type: str | None = None
    enrollment_count: int | None = None


class CreateSubjectOfferingRequest(BaseModel):
    subject_id: int
    faculty_id: int
    academic_year: str
    semester_type: str
    section: str = "A"
    branch_id: int | None = None
    semester: int


class UpdateSubjectOfferingRequest(BaseModel):
    faculty_id: int | None = None
    section: str | None = None
    active: bool | None = None


class OfferingListResponse(BaseModel):
    items: list[SubjectOfferingOut]
    pagination: PaginationMeta


# ---------------------------------------------------------------------------
# Enrollment
# ---------------------------------------------------------------------------

class EnrollmentOut(BaseModel):
    id: int
    student_id: int
    usn: str
    student_name: str
    subject_offering_id: int
    subject_code: str
    subject_name: str
    enrollment_type: str


class EnrollmentListResponse(BaseModel):
    items: list[EnrollmentOut]
    pagination: PaginationMeta


# ---------------------------------------------------------------------------
# Timetable
# ---------------------------------------------------------------------------

class TimetableSlotOut(BaseModel):
    id: int
    subject_offering_id: int
    subject_code: str
    subject_name: str
    faculty_name: str
    day_of_week: str
    slot_number: int
    start_time: time
    end_time: time
    room: str
    effective_from: date
    effective_until: date | None = None


class TimetableSlotCreate(BaseModel):
    subject_offering_id: int
    day_of_week: str = Field(pattern=r"^(MON|TUE|WED|THU|FRI|SAT)$")
    slot_number: int
    start_time: time
    end_time: time
    room: str = ""
    effective_from: date
    effective_until: date | None = None
    academic_year_id: int


# ---------------------------------------------------------------------------
# Substitute
# ---------------------------------------------------------------------------

class SubstituteOut(BaseModel):
    id: int
    date: date
    timetable_slot_id: int | None = None
    subject_offering_id: int
    subject_code: str
    original_faculty_name: str
    substitute_faculty_name: str | None = None
    reason: str
    status: str
    assigned_by_name: str


class SubstituteCreate(BaseModel):
    date: date
    timetable_slot_id: int | None = None
    subject_offering_id: int
    original_faculty_id: int
    substitute_faculty_id: int | None = None
    reason: str


class SubstituteUpdate(BaseModel):
    substitute_faculty_id: int | None = None
    status: str | None = None


# ---------------------------------------------------------------------------
# Attendance Session
# ---------------------------------------------------------------------------

class ActiveSessionOut(BaseModel):
    id: int
    subject_offering_id: int
    subject_code: str
    subject_name: str
    faculty_name: str
    session_type: str
    starts_at: datetime
    ends_at: datetime
    radius_meters: int


class StartSessionRequest(BaseModel):
    subject_offering_id: int
    session_type: str = Field(default="lecture", pattern=r"^(lecture|lab|tutorial)$")
    teacher_latitude: float
    teacher_longitude: float
    radius_meters: int = 10
    duration_minutes: int = 5


class StartSessionResponse(BaseModel):
    id: int
    code: str
    starts_at: datetime
    ends_at: datetime
    radius_meters: int


# ---------------------------------------------------------------------------
# Attendance Record
# ---------------------------------------------------------------------------

class MarkAttendanceRequest(BaseModel):
    session_id: int
    entered_code: str = Field(min_length=4, max_length=4)
    student_latitude: float
    student_longitude: float
    gps_accuracy_meters: float
    device_id: str | None = None


class MarkAttendanceResponse(BaseModel):
    status: str
    distance_from_teacher: float
    marked_at: datetime


class AttendanceRecordOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    usn: str
    status: str
    distance_from_teacher: float
    marked_at: datetime


class AttendanceCorrectionRequest(BaseModel):
    new_status: str = Field(pattern=r"^(present|absent|late|excused)$")
    reason: str = Field(min_length=5)


class AttendanceCorrectionOut(BaseModel):
    id: int
    record_id: int | None = None
    session_id: int
    student_id: int
    student_name: str
    usn: str
    old_status: str
    new_status: str
    reason: str
    corrected_by_name: str
    corrected_at: datetime


# ---------------------------------------------------------------------------
# Attendance Summary & Reports
# ---------------------------------------------------------------------------

class AttendanceSummaryOut(BaseModel):
    subject_offering_id: int
    subject_code: str
    subject_name: str
    total_sessions: int
    present_sessions: int
    percentage: float


class DefaulterOut(BaseModel):
    usn: str
    student_name: str
    subject_code: str
    subject_name: str
    total_sessions: int
    present_sessions: int
    percentage: float


class DashboardMetrics(BaseModel):
    total_students: int
    total_faculty: int
    total_departments: int
    total_subjects: int
    total_offerings: int
    total_sessions: int
    active_sessions: int
    total_attendance_records: int


# ---------------------------------------------------------------------------
# Danger alerts
# ---------------------------------------------------------------------------

class AttendanceAlert(BaseModel):
    subject_code: str
    subject_name: str
    percentage: float
    level: str  # "warning" (< 85%) or "critical" (< 75%)


# ---------------------------------------------------------------------------
# Import response
# ---------------------------------------------------------------------------

class ImportError(BaseModel):
    row: int
    field: str
    error: str


class ImportResponse(BaseModel):
    imported: int
    errors: list[ImportError]


# ---------------------------------------------------------------------------
# Leave and condonation
# ---------------------------------------------------------------------------

class LeaveRequestCreate(BaseModel):
    leave_type: str = Field(pattern=r"^(medical|od|personal)$")
    start_date: date
    end_date: date
    reason: str = Field(min_length=5)
    document_path: str | None = None


class LeaveRequestOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    usn: str
    leave_type: str
    start_date: date
    end_date: date
    reason: str
    document_path: str | None = None
    status: str
    reviewed_by_name: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime


class CondonationRequestCreate(BaseModel):
    subject_offering_id: int
    reason: str = Field(min_length=5)


class CondonationRequestOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    usn: str
    subject_offering_id: int
    subject_code: str
    subject_name: str
    current_percentage: float
    reason: str
    status: str
    reviewed_by_name: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime


class ReviewRequest(BaseModel):
    status: str = Field(pattern=r"^(approved|rejected)$")
