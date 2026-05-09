from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers import admin, auth, faculty, hod, student

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Smart Attendance System",
    version="2.0.0",
    description="College-scale attendance system for BMSIT",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount admin web static files
admin_dir = Path(__file__).resolve().parents[2] / "admin-web"
if admin_dir.exists():
    app.mount("/admin/assets", StaticFiles(directory=admin_dir), name="admin-assets")

# Include routers
app.include_router(auth.router)
app.include_router(student.router)
app.include_router(faculty.router)
app.include_router(hod.router)
app.include_router(admin.router)


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/admin", include_in_schema=False)
def admin_home():
    index = admin_dir / "index.html"
    if not index.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="admin_web_not_found")
    return FileResponse(index)
