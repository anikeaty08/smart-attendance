from app.database import Base, SessionLocal, engine
from app.models import Department, Faculty
from app.security import hash_password


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Faculty).filter(Faculty.is_admin.is_(True)).count():
            print("Seed data already exists — admin user found.")
            return

        # Departments
        departments = [
            ("Computer Science and Engineering", "CSE"),
            ("Information Science and Engineering", "ISE"),
            ("Artificial Intelligence and Machine Learning", "AIML"),
            ("Electronics and Communication Engineering", "ECE"),
            ("Mechanical Engineering", "ME"),
            ("Civil Engineering", "CV"),
            ("Electrical and Electronics Engineering", "EEE"),
        ]
        dept_objs = []
        for name, code in departments:
            dept = Department(name=name, code=code)
            db.add(dept)
            dept_objs.append(dept)
        db.flush()

        # Admin user (college-level, no department)
        admin = Faculty(
            name="Admin",
            email="admin@bmsit.in",
            department_id=None,
            is_admin=True,
            is_hod=False,
            password_hash=hash_password("admin123"),
        )
        db.add(admin)
        db.commit()
        print(f"Seeded {len(departments)} departments and admin user (admin@bmsit.in / admin123)")
    finally:
        db.close()


if __name__ == "__main__":
    run()
