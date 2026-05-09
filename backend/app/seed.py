from app.database import Base, SessionLocal, engine
from app.models import Department, Faculty


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
        for name, code in departments:
            db.add(Department(name=name, code=code))
        db.flush()

        # Admin user — no password stored here.
        # The admin logs in via Clerk (email + OTP or password set in Clerk dashboard).
        # The backend just checks that admin@bmsit.in exists in the faculty table with is_admin=True.
        admin = Faculty(
            name="Admin",
            email="admin@bmsit.in",
            department_id=None,
            is_admin=True,
            is_hod=False,
        )
        db.add(admin)
        db.commit()
        print(f"Seeded {len(departments)} departments.")
        print("Seeded admin user: admin@bmsit.in")
        print("NOTE: Set this user's password in the Clerk dashboard to enable web login.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
