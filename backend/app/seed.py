from app.database import Base, SessionLocal, engine
from app.models import Department, Faculty, Student, StudentEnrollment, Subject, SubjectOffering


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Student).count():
            print("Seed data already exists")
            return
        cse = Department(name="Computer Science and Engineering", code="CSE")
        db.add(cse)
        db.flush()

        student = Student(
            usn="1BY23CS001",
            name="Demo Student",
            email="student1@student.bmsit.in",
            branch_id=cse.id,
            current_semester=4,
        )
        faculty = Faculty(name="Demo Faculty", email="faculty1@bmsit.in", department_id=cse.id)
        admin = Faculty(name="Admin User", email="admin@bmsit.in", department_id=cse.id, is_admin=True)
        db.add_all([student, faculty, admin])
        db.flush()

        dbms = Subject(subject_code="BCS401", subject_name="Database Management Systems", credits=4, semester=4, department_id=cse.id)
        os = Subject(subject_code="BCS402", subject_name="Operating Systems", credits=4, semester=4, department_id=cse.id)
        db.add_all([dbms, os])
        db.flush()

        offering = SubjectOffering(
            subject_id=dbms.id,
            faculty_id=faculty.id,
            academic_year="2025-26",
            semester_type="even",
            section="A",
            branch_id=cse.id,
            semester=4,
        )
        other_offering = SubjectOffering(
            subject_id=os.id,
            faculty_id=faculty.id,
            academic_year="2025-26",
            semester_type="even",
            section="A",
            branch_id=cse.id,
            semester=4,
        )
        db.add_all([offering, other_offering])
        db.flush()
        db.add(StudentEnrollment(student_id=student.id, subject_offering_id=offering.id, enrollment_type="core"))
        db.commit()
        print("Seeded demo data")
    finally:
        db.close()


if __name__ == "__main__":
    run()

