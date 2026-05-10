import sys
import os

# Ensure the app module can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import Faculty, FirstLoginVerification

def seed_test_users():
    db = SessionLocal()
    try:
        users_to_create = [
            {
                "email": "principal@bmsit.in",
                "name": "Principal",
                "is_admin": True,
                "is_hod": True,
            },
            {
                "email": "admin@bmsit.in",
                "name": "System Admin",
                "is_admin": True,
                "is_hod": False,
            },
            {
                "email": "hod@bmsit.in",
                "name": "Head of Department",
                "is_admin": False,
                "is_hod": True,
            }
        ]
        
        for user_data in users_to_create:
            # Check if faculty exists
            faculty = db.query(Faculty).filter(Faculty.email == user_data["email"]).first()
            if not faculty:
                faculty = Faculty(
                    email=user_data["email"],
                    name=user_data["name"],
                    is_admin=user_data["is_admin"],
                    is_hod=user_data["is_hod"]
                )
                db.add(faculty)
                db.commit()
                print(f"Created faculty: {user_data['email']}")
            else:
                print(f"Faculty already exists: {user_data['email']}")
                
            # Auto-verify them
            verification = db.query(FirstLoginVerification).filter(FirstLoginVerification.email == user_data["email"]).first()
            if not verification:
                verification = FirstLoginVerification(
                    email=user_data["email"],
                    verified=True,
                    attempts=0
                )
                db.add(verification)
                db.commit()
                print(f"Auto-verified: {user_data['email']}")
            elif not verification.verified:
                verification.verified = True
                db.commit()
                print(f"Set to verified: {user_data['email']}")
                
        print("Done seeding test users.")
    finally:
        db.close()

if __name__ == "__main__":
    seed_test_users()
