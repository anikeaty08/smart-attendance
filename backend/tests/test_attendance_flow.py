import os

os.environ["DATABASE_URL"] = "postgresql+psycopg://postgres:aniket@localhost/attendance_test"


def ensure_test_database() -> None:
    import psycopg

    with psycopg.connect("postgresql://postgres:aniket@localhost/postgres", autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = 'attendance_test'")
            if cur.fetchone() is None:
                cur.execute("CREATE DATABASE attendance_test")


ensure_test_database()

import pytest
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import (
    Department,
    Faculty,
    FirstLoginVerification,
    Student,
    StudentEnrollment,
    Subject,
    SubjectOffering,
)
from app.security import bearer_scheme, find_user_by_email, get_current_user


def override_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    if not credentials:
        raise HTTPException(status_code=401, detail="not_authenticated")
    db = SessionLocal()
    try:
        role, user = find_user_by_email(db, credentials.credentials)
        if not user:
            raise HTTPException(status_code=403, detail="user_not_registered")
        return {"role": role, "user": user}
    finally:
        db.close()


app.dependency_overrides[get_current_user] = override_current_user


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        cse = Department(name="Computer Science and Engineering", code="CSE")
        db.add(cse)
        db.flush()
        student = Student(usn="1BY23CS001", name="Demo Student", email="student1@student.bmsit.in", branch_id=cse.id, current_semester=4)
        other = Student(usn="1BY23CS999", name="Other Student", email="student2@student.bmsit.in", branch_id=cse.id, current_semester=4)
        faculty = Faculty(name="Demo Faculty", email="faculty1@bmsit.in", department_id=cse.id)
        hod = Faculty(name="Demo HOD", email="hod@bmsit.in", department_id=cse.id, is_hod=True)
        admin = Faculty(name="Admin User", email="admin@bmsit.in", department_id=cse.id, is_admin=True)
        db.add_all([student, other, faculty, hod, admin])
        db.flush()
        dbms = Subject(subject_code="BCS401", subject_name="Database Management Systems", credits=4, semester=4, department_id=cse.id)
        os = Subject(subject_code="BCS402", subject_name="Operating Systems", credits=4, semester=4, department_id=cse.id)
        db.add_all([dbms, os])
        db.flush()
        enrolled = SubjectOffering(subject_id=dbms.id, faculty_id=faculty.id, academic_year="2025-26", semester_type="even", section="A", branch_id=cse.id, semester=4)
        hidden = SubjectOffering(subject_id=os.id, faculty_id=faculty.id, academic_year="2025-26", semester_type="even", section="A", branch_id=cse.id, semester=4)
        db.add_all([enrolled, hidden])
        db.flush()
        db.add(StudentEnrollment(student_id=student.id, subject_offering_id=enrolled.id, enrollment_type="core"))
        for email in [
            "student1@student.bmsit.in",
            "student2@student.bmsit.in",
            "faculty1@bmsit.in",
            "hod@bmsit.in",
            "admin@bmsit.in",
        ]:
            db.add(FirstLoginVerification(email=email, verified=True))
        db.commit()
    finally:
        db.close()
    yield


client = TestClient(app)


def token(email: str) -> str:
    return email


def test_student_sees_only_enrolled_subjects():
    response = client.get("/student/subjects", headers={"Authorization": f"Bearer {token('student1@student.bmsit.in')}"})
    assert response.status_code == 200
    rows = response.json()
    assert [row["subject_code"] for row in rows] == ["BCS401"]


def test_full_attendance_flow_accepts_valid_location_and_code():
    faculty_token = token("faculty1@bmsit.in")
    student_token = token("student1@student.bmsit.in")

    start = client.post(
        "/faculty/sessions/start",
        headers={"Authorization": f"Bearer {faculty_token}"},
        json={
            "subject_offering_id": 1,
            "session_type": "lecture",
            "teacher_latitude": 12.9716,
            "teacher_longitude": 77.5946,
            "radius_meters": 10,
            "duration_minutes": 5,
        },
    )
    assert start.status_code == 200, start.text
    code = start.json()["code"]

    active = client.get("/student/active-sessions", headers={"Authorization": f"Bearer {student_token}"})
    assert active.status_code == 200
    assert len(active.json()) == 1

    mark = client.post(
        "/student/attendance/mark",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "session_id": start.json()["id"],
            "entered_code": code,
            "student_latitude": 12.9716001,
            "student_longitude": 77.5946001,
            "gps_accuracy_meters": 8,
            "device_id": "device-a",
        },
    )
    assert mark.status_code == 200, mark.text
    assert mark.json()["status"] == "present"

    duplicate = client.post(
        "/student/attendance/mark",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "session_id": start.json()["id"],
            "entered_code": code,
            "student_latitude": 12.9716001,
            "student_longitude": 77.5946001,
            "gps_accuracy_meters": 8,
            "device_id": "device-a",
        },
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "already_marked"


def test_non_enrolled_student_cannot_mark_attendance():
    faculty_token = token("faculty1@bmsit.in")
    other_token = token("student2@student.bmsit.in")
    start = client.post(
        "/faculty/sessions/start",
        headers={"Authorization": f"Bearer {faculty_token}"},
        json={
            "subject_offering_id": 1,
            "session_type": "lecture",
            "teacher_latitude": 12.9716,
            "teacher_longitude": 77.5946,
            "radius_meters": 10,
            "duration_minutes": 5,
        },
    )
    response = client.post(
        "/student/attendance/mark",
        headers={"Authorization": f"Bearer {other_token}"},
        json={
            "session_id": start.json()["id"],
            "entered_code": start.json()["code"],
            "student_latitude": 12.9716001,
            "student_longitude": 77.5946001,
            "gps_accuracy_meters": 8,
            "device_id": "device-b",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "not_enrolled"


def test_invalid_location_and_accuracy_are_rejected():
    faculty_token = token("faculty1@bmsit.in")
    student_token = token("student1@student.bmsit.in")
    start = client.post(
        "/faculty/sessions/start",
        headers={"Authorization": f"Bearer {faculty_token}"},
        json={
            "subject_offering_id": 1,
            "session_type": "lecture",
            "teacher_latitude": 12.9716,
            "teacher_longitude": 77.5946,
            "radius_meters": 10,
            "duration_minutes": 5,
        },
    )
    far = client.post(
        "/student/attendance/mark",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "session_id": start.json()["id"],
            "entered_code": start.json()["code"],
            "student_latitude": 13.0,
            "student_longitude": 77.7,
            "gps_accuracy_meters": 8,
            "device_id": "device-c",
        },
    )
    assert far.status_code == 400
    assert far.json()["detail"] == "outside_radius"


def test_failed_attempts_lock_attendance_session():
    faculty_token = token("faculty1@bmsit.in")
    student_token = token("student1@student.bmsit.in")
    start = client.post(
        "/faculty/sessions/start",
        headers={"Authorization": f"Bearer {faculty_token}"},
        json={
            "subject_offering_id": 1,
            "session_type": "lecture",
            "teacher_latitude": 12.9716,
            "teacher_longitude": 77.5946,
            "radius_meters": 10,
            "duration_minutes": 5,
        },
    )
    for _ in range(5):
        response = client.post(
            "/student/attendance/mark",
            headers={"Authorization": f"Bearer {student_token}"},
            json={
                "session_id": start.json()["id"],
                "entered_code": "9999",
                "student_latitude": 12.9716001,
                "student_longitude": 77.5946001,
                "gps_accuracy_meters": 8,
                "device_id": "device-lock",
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "invalid_code"

    locked = client.post(
        "/student/attendance/mark",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "session_id": start.json()["id"],
            "entered_code": start.json()["code"],
            "student_latitude": 12.9716001,
            "student_longitude": 77.5946001,
            "gps_accuracy_meters": 8,
            "device_id": "device-lock",
        },
    )
    assert locked.status_code == 423
    assert locked.json()["detail"] == "attendance_locked_for_session"


def test_leave_and_condonation_request_review_flow():
    student_token = token("student1@student.bmsit.in")
    hod_token = token("hod@bmsit.in")

    leave = client.post(
        "/student/leave-requests",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "leave_type": "medical",
            "start_date": "2026-05-10",
            "end_date": "2026-05-11",
            "reason": "Medical appointment",
        },
    )
    assert leave.status_code == 200, leave.text
    reviewed = client.put(
        f"/hod/leave-requests/{leave.json()['id']}/review",
        headers={"Authorization": f"Bearer {hod_token}"},
        json={"status": "approved"},
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["status"] == "approved"

    condonation = client.post(
        "/student/condonation-requests",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"subject_offering_id": 1, "reason": "Medical shortage request"},
    )
    assert condonation.status_code == 200, condonation.text
    reviewed_condonation = client.put(
        f"/hod/condonation-requests/{condonation.json()['id']}/review",
        headers={"Authorization": f"Bearer {hod_token}"},
        json={"status": "rejected"},
    )
    assert reviewed_condonation.status_code == 200, reviewed_condonation.text
    assert reviewed_condonation.json()["status"] == "rejected"


def test_faculty_report_uses_present_records_not_enrolled_count():
    faculty_token = token("faculty1@bmsit.in")
    student_token = token("student1@student.bmsit.in")
    start = client.post(
        "/faculty/sessions/start",
        headers={"Authorization": f"Bearer {faculty_token}"},
        json={
            "subject_offering_id": 1,
            "session_type": "lecture",
            "teacher_latitude": 12.9716,
            "teacher_longitude": 77.5946,
            "radius_meters": 10,
            "duration_minutes": 5,
        },
    )
    client.post(
        "/student/attendance/mark",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "session_id": start.json()["id"],
            "entered_code": start.json()["code"],
            "student_latitude": 12.9716001,
            "student_longitude": 77.5946001,
            "gps_accuracy_meters": 8,
            "device_id": "device-report",
        },
    )
    report = client.get("/faculty/attendance/report", headers={"Authorization": f"Bearer {faculty_token}"})
    assert report.status_code == 200
    first = next(row for row in report.json() if row["subject_offering_id"] == 1)
    assert first["total_sessions"] == 1
    assert first["present_sessions"] == 1
    assert first["percentage"] == 100.0
