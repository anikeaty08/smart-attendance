from __future__ import annotations

import os

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Faculty, FirstLoginVerification, Student
from scripts.provision_aiml_users import ClerkProvisioner, ensure_aiml_records


SELECTED_FACULTY = [
    ("principal@bmsit.in", "Dr. Sanjay H A", "admin"),
    ("s.megha@bmsit.in", "Prof. Megha S", "hod"),
    ("hod_aiml@bmsit.in", "AIML HOD", "hod"),
    ("pradeepkr@bmsit.in", "Dr. Pradeep K R", "faculty"),
    ("balaraju.g@bmsit.in", "Prof. Balaraju G", "faculty"),
]

SELECTED_STUDENTS = [337, 371, 391]


def update_local_verification() -> None:
    ensure_aiml_records()
    db = SessionLocal()
    try:
        for email, name, role in SELECTED_FACULTY:
            faculty = db.scalar(select(Faculty).where(Faculty.email == email))
            if faculty:
                faculty.name = name
                faculty.is_admin = role == "admin" or faculty.is_admin
                faculty.is_hod = role == "hod" or faculty.is_hod
            verification = db.scalar(select(FirstLoginVerification).where(FirstLoginVerification.email == email))
            if not verification:
                verification = FirstLoginVerification(email=email)
                db.add(verification)
            verification.verified = True
            verification.otp_hash = None
            verification.attempts = 0

        for number in SELECTED_STUDENTS:
            email = f"24ug1byai{number:03d}@bmsit.in"
            student = db.scalar(select(Student).where(Student.email == email))
            if student:
                student.current_semester = 4
            verification = db.scalar(select(FirstLoginVerification).where(FirstLoginVerification.email == email))
            if not verification:
                verification = FirstLoginVerification(email=email)
                db.add(verification)
            verification.verified = False
            verification.otp_hash = None
            verification.attempts = 0
        db.commit()
    finally:
        db.close()


def main() -> None:
    update_local_verification()
    provisioner = ClerkProvisioner(os.environ["CLERK_SECRET_KEY"])
    counts = {"created": 0, "updated": 0}
    try:
        for email, name, role in SELECTED_FACULTY:
            result = provisioner.create_or_update_user(email=email, name=name, role=role, external_id=email)
            counts[result] += 1
            user_id = provisioner.find_user_id(email)
            if user_id:
                provisioner.client.patch(
                    f"/users/{user_id}/metadata",
                    json={
                        "public_metadata": {
                            "role": role,
                            "department": "AIML",
                            "must_change_password": False,
                            "first_login_verified": True,
                            "first_login_otp_required": False,
                        }
                    },
                ).raise_for_status()

        for number in SELECTED_STUDENTS:
            email = f"24ug1byai{number:03d}@bmsit.in"
            name = f"AIML Student {number:03d}"
            result = provisioner.create_or_update_user(email=email, name=name, role="student", external_id=f"24UG1BYAI{number:03d}")
            counts[result] += 1
            user_id = provisioner.find_user_id(email)
            if user_id:
                provisioner.client.patch(
                    f"/users/{user_id}/metadata",
                    json={
                        "public_metadata": {
                            "role": "student",
                            "department": "AIML",
                            "must_change_password": True,
                            "first_login_verified": False,
                            "first_login_otp_required": True,
                        }
                    },
                ).raise_for_status()
        print(counts)
    finally:
        provisioner.close()


if __name__ == "__main__":
    main()

