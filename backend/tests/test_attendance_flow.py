from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import (
    Department,
    Faculty,
    Student,
    StudentEnrollment,
    Subject,
    SubjectOffering,
)


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
        admin = Faculty(name="Admin User", email="admin@bmsit.in", department_id=cse.id, is_admin=True)
        db.add_all([student, other, faculty, admin])
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
        db.commit()
    finally:
        db.close()
    yield


client = TestClient(app)


def token(email: str) -> str:
    response = client.post("/auth/google", json={"email": email})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


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

