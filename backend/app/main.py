from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.routers import admin, auth, faculty, hod, student

app = FastAPI(
    title="Smart Attendance System",
    version="2.0.0",
    description="College-scale attendance system for BMSIT",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
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
        return RedirectResponse("http://127.0.0.1:3000")
    return FileResponse(index)
