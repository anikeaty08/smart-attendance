from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    email: EmailStr
    name: str


class GoogleLoginRequest(BaseModel):
    id_token: str | None = None
    email: EmailStr | None = None


class MeResponse(BaseModel):
    id: int
    role: str
    email: EmailStr
    name: str
    is_admin: bool = False


class SubjectOfferingOut(BaseModel):
    id: int
    subject_code: str
    subject_name: str
    faculty_name: str
    academic_year: str
    semester_type: str
    section: str
    semester: int
    enrollment_type: str | None = None


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
    session_type: str = Field(default="lecture", pattern="^(lecture|lab|tutorial)$")
    teacher_latitude: float
    teacher_longitude: float
    radius_meters: int = 10
    duration_minutes: int = 5


class CreateSubjectOfferingRequest(BaseModel):
    subject_id: int
    faculty_id: int
    academic_year: str
    semester_type: str
    section: str = "A"
    branch_id: int | None = None
    semester: int


class StartSessionResponse(BaseModel):
    id: int
    code: str
    starts_at: datetime
    ends_at: datetime
    radius_meters: int


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


class AttendanceSummaryOut(BaseModel):
    subject_offering_id: int
    subject_code: str
    subject_name: str
    total_sessions: int
    present_sessions: int
    percentage: float
