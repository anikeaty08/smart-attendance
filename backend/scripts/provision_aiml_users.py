from __future__ import annotations

import argparse
import os
import time
from dataclasses import dataclass

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models import AccountStatus, Department, Faculty, FirstLoginVerification, Student


INITIAL_PASSWORD = "pass123"
CLERK_API = "https://api.clerk.com/v1"


@dataclass(frozen=True)
class FacultyInput:
    name: str
    email: str
    is_admin: bool = False
    is_hod: bool = False


FACULTY: list[FacultyInput] = [
    FacultyInput("Dr. Sanjay H A", "principal@bmsit.in", is_admin=True),
    FacultyInput("Dr. Anupama H S", "anupamahs@bmsit.in", is_hod=True),
    FacultyInput("Dr. Pradeep K R", "pradeepkr@bmsit.in"),
    FacultyInput("Dr. Bharathi Malakreddy A", "bharathi_m@bmsit.in"),
    FacultyInput("Dr. Hemamalini B H", "bhhemaraj@bmsit.in"),
    FacultyInput("Dr. Srivani P", "srivanicse@bmsit.in"),
    FacultyInput("Dr. Manoj H M", "manojhm@bmsit.in"),
    FacultyInput("Dr. Niranjanamurthy M", "niruhsd@bmsit.in"),
    FacultyInput("Dr. Karthik Vasu", "v.karthik@bmsit.in"),
    FacultyInput("Dr. Kantharaju V", "kanth95@bmsit.in"),
    FacultyInput("Dr. Rajesh I S", "rajeshaiml@bmsit.in"),
    FacultyInput("Prof. Megha S", "s.megha@bmsit.in"),
    FacultyInput("Prof. Balaraju G", "balaraju.g@bmsit.in"),
    FacultyInput("Prof. Shruthi.S", "shruthis@bmsit.in"),
    FacultyInput("Prof. Mayuri K P", "mayuri@bmsit.in"),
    FacultyInput("Prof. Kavitha D", "kavitha.d@bmsit.in"),
    FacultyInput("Prof. Umesh T", "umesht@bmsit.in"),
    FacultyInput("Dr. Sowmya V L", "soumyavl@bmsit.in"),
    FacultyInput("Manasa K", "manasak@bmsit.in"),
    FacultyInput("Pragathi M", "pragathim@bmsit.in"),
    FacultyInput("Prof. Bhavika Rajora", "bhavika@bmsit.in"),
    FacultyInput("Prof. Srujana S", "srujana.s@bmsit.in"),
    FacultyInput("Prof. Syed Owais Umair", "umair@bmsit.in"),
    FacultyInput("Chethana G", "chethanag@bmsit.in"),
    FacultyInput("Prof. Shilpa Prabhu Patil", "shilpa.patil@bmsit.in"),
    FacultyInput("Prof. Pavithra G", "pavithrag@bmsit.in"),
    FacultyInput("Pavan Mulgund", "pavan@bmsit.in"),
    FacultyInput("Indumathi S", "indumathi@bmsit.in"),
    FacultyInput("Dr. Sampath Kumar Y R", "samkumar@bmsit.in"),
    FacultyInput("Prof. Hamsaveni M", "hamsaveni@bmsit.in"),
    FacultyInput("Prof. Lakshmi M R", "lakshmimr@bmsit.in"),
    FacultyInput("Prof. Ashwini S S", "ashwini.ss@bmsit.in"),
    FacultyInput("Salma Itagi", "salma.itagi@bmsit.in"),
    FacultyInput("Prof. Amitha S K", "amitha@bmsit.in"),
    FacultyInput("Prof. Abhishek K L", "abhishek@bmsit.in"),
    FacultyInput("Dr. Chidananda K", "chidananda.k@bmsit.in"),
    FacultyInput("Prof. Shobhit Tembhre", "shobhit@bmsit.in"),
    FacultyInput("Prof. Sanjay M Belgaonkar", "sanjaymb@bmsit.in"),
    FacultyInput("Prof. Yatheesh N G", "yatheesh@bmsit.in"),
    FacultyInput("Dr. Archana Bhat", "archanabhat@bmsit.in"),
]


def split_name(name: str) -> tuple[str, str]:
    parts = name.replace("Dr. ", "").replace("Prof. ", "").split()
    if len(parts) <= 1:
        return name, ""
    return parts[0], " ".join(parts[1:])


def student_section(number: int) -> str:
    if number <= 130:
        return "A"
    if number <= 260:
        return "B"
    return "C"


def ensure_aiml_records() -> tuple[int, int]:
    db = SessionLocal()
    try:
        dept = db.scalar(select(Department).where(Department.code == "AIML"))
        if not dept:
            dept = Department(name="Artificial Intelligence and Machine Learning", code="AIML")
            db.add(dept)
            db.flush()

        students_changed = 0
        for number in range(1, 392):
            email = f"24ug1byai{number:03d}@bmsit.in"
            usn = f"24UG1BYAI{number:03d}"
            student = db.scalar(select(Student).where(Student.email == email))
            if not student:
                student = Student(
                    usn=usn,
                    name=f"AIML Student {number:03d}",
                    email=email,
                    branch_id=dept.id,
                    batch_year=2024,
                    current_semester=4,
                    section=student_section(number),
                    status=AccountStatus.active.value,
                )
                db.add(student)
                students_changed += 1
            else:
                student.usn = usn
                student.branch_id = dept.id
                student.batch_year = 2024
                student.current_semester = 4
                student.section = student_section(number)
                student.status = AccountStatus.active.value
            verification = db.scalar(select(FirstLoginVerification).where(FirstLoginVerification.email == email))
            if not verification:
                db.add(FirstLoginVerification(email=email, verified=False, attempts=0))

        faculty_changed = 0
        for item in FACULTY:
            email = item.email.lower()
            faculty = db.scalar(select(Faculty).where(Faculty.email == email))
            if not faculty:
                faculty = Faculty(
                    name=item.name,
                    email=email,
                    department_id=dept.id,
                    is_admin=item.is_admin,
                    is_hod=item.is_hod,
                    status=AccountStatus.active.value,
                )
                db.add(faculty)
                faculty_changed += 1
            else:
                faculty.name = item.name
                faculty.department_id = dept.id
                faculty.is_admin = faculty.is_admin or item.is_admin
                faculty.is_hod = faculty.is_hod or item.is_hod
                faculty.status = AccountStatus.active.value
            verification = db.scalar(select(FirstLoginVerification).where(FirstLoginVerification.email == email))
            if not verification:
                db.add(FirstLoginVerification(email=email, verified=False, attempts=0))

        db.commit()
        return students_changed, faculty_changed
    except IntegrityError:
        db.rollback()
        raise
    finally:
        db.close()


class ClerkProvisioner:
    def __init__(self, secret_key: str) -> None:
        self.client = httpx.Client(
            base_url=CLERK_API,
            headers={"Authorization": f"Bearer {secret_key}", "Content-Type": "application/json"},
            timeout=30,
        )

    def close(self) -> None:
        self.client.close()

    def find_user_id(self, email: str) -> str | None:
        response = self.client.get("/users", params={"email_address": email})
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and data:
            return data[0]["id"]
        return None

    def create_or_update_user(self, *, email: str, name: str, role: str, external_id: str) -> str:
        first_name, last_name = split_name(name)
        metadata = {
            "role": role,
            "department": "AIML",
            "must_change_password": True,
            "first_login_verified": False,
            "first_login_otp_required": True,
            "initial_password_set": True,
        }
        payload = {
            "email_address": [email],
            "password": INITIAL_PASSWORD,
            "skip_password_checks": True,
            "skip_legal_checks": True,
            "first_name": first_name,
            "last_name": last_name,
            "external_id": external_id,
            "public_metadata": metadata,
            "private_metadata": {"source": "aiml_real_user_provisioning"},
        }

        user_id = self.find_user_id(email)
        if user_id:
            update_payload = {
                "password": INITIAL_PASSWORD,
                "skip_password_checks": True,
                "first_name": first_name,
                "last_name": last_name,
                "public_metadata": metadata,
                "private_metadata": {"source": "aiml_real_user_provisioning"},
            }
            response = self.client.patch(f"/users/{user_id}", json=update_payload)
            response.raise_for_status()
            return "updated"

        response = self.client.post("/users", json=payload)
        response.raise_for_status()
        return "created"


def provision_clerk(secret_key: str, limit: int | None = None) -> dict[str, int]:
    provisioner = ClerkProvisioner(secret_key)
    counts = {"created": 0, "updated": 0}
    try:
        users: list[tuple[str, str, str, str]] = []
        for number in range(1, 392):
            email = f"24ug1byai{number:03d}@bmsit.in"
            users.append((email, f"AIML Student {number:03d}", "student", f"24UG1BYAI{number:03d}"))
        for item in FACULTY:
            role = "admin" if item.is_admin else "hod" if item.is_hod else "faculty"
            users.append((item.email.lower(), item.name, role, item.email.lower()))

        for index, (email, name, role, external_id) in enumerate(users[:limit], start=1):
            result = provisioner.create_or_update_user(email=email, name=name, role=role, external_id=external_id)
            counts[result] += 1
            if index % 75 == 0:
                time.sleep(10)
            else:
                time.sleep(0.12)
        return counts
    finally:
        provisioner.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Provision real AIML users in PostgreSQL and Clerk.")
    parser.add_argument("--clerk", action="store_true", help="Also create/update users in Clerk.")
    parser.add_argument("--limit", type=int, default=None, help="Limit Clerk users for a small smoke run.")
    args = parser.parse_args()

    students_changed, faculty_changed = ensure_aiml_records()
    print(f"PostgreSQL upsert complete: {students_changed} new students, {faculty_changed} new faculty.")

    if args.clerk:
        secret_key = os.environ.get("CLERK_SECRET_KEY")
        if not secret_key:
            raise SystemExit("CLERK_SECRET_KEY is required for Clerk provisioning.")
        counts = provision_clerk(secret_key, args.limit)
        print(f"Clerk provisioning complete: {counts['created']} created, {counts['updated']} updated.")


if __name__ == "__main__":
    main()
