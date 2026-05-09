# Smart Attendance System

College-scale smart attendance MVP for 10,000+ students.

## Stack

- Backend: FastAPI + SQLAlchemy
- Database: PostgreSQL in production, SQLite by default for local development
- Admin panel: Static web dashboard served by FastAPI
- Android: Kotlin native project skeleton

## Quick Start

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload
```

Open:

- API docs: http://127.0.0.1:8000/docs
- Admin web: http://127.0.0.1:8000/admin

Local auth accepts a college email directly at `POST /auth/google`. In production, set `GOOGLE_CLIENT_ID` and wire Google ID token verification.

## Demo Users

Seed data creates:

- Student: `student1@student.bmsit.in`
- Faculty: `faculty1@bmsit.in`
- Admin: `admin@bmsit.in`

