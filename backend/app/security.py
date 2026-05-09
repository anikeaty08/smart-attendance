from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import secrets
from typing import Literal

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import AccountStatus, Faculty, Student

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/google", auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Password hashing (for admin/HOD web login)
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# Session code hashing (4-digit attendance code)
# ---------------------------------------------------------------------------

def hash_code(code: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.sha256(f"{salt}:{code}".encode("utf-8")).hexdigest()
    return f"{salt}${digest}"


def verify_code(code: str, code_hash: str) -> bool:
    try:
        salt, expected = code_hash.split("$", 1)
    except ValueError:
        return False
    actual = hashlib.sha256(f"{salt}:{code}".encode("utf-8")).hexdigest()
    return hmac.compare_digest(actual, expected)


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------

def create_access_token(subject: str, role: str, user_id: int) -> str:
    expires = datetime.now(UTC) + timedelta(minutes=settings.access_token_minutes)
    payload = {"sub": subject, "role": role, "uid": user_id, "exp": expires}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# ---------------------------------------------------------------------------
# Domain validation (single domain: bmsit.in)
# ---------------------------------------------------------------------------

def _domain(email: str) -> str:
    return email.split("@", 1)[1].lower()


def validate_allowed_domain(email: str) -> None:
    domain = _domain(email)
    if domain not in settings.domains:
        raise HTTPException(status_code=403, detail="email_domain_not_allowed")


# ---------------------------------------------------------------------------
# Role detection from DB (all @bmsit.in)
# ---------------------------------------------------------------------------

def find_user_by_email(db: Session, email: str):
    """Look up user by email and return (role, user_obj).

    Order: students table first, then faculty.
    Faculty role is determined by is_admin / is_hod flags.
    """
    student = db.scalar(select(Student).where(Student.email == email.lower()))
    if student:
        return "student", student
    faculty = db.scalar(select(Faculty).where(Faculty.email == email.lower()))
    if faculty:
        if faculty.is_admin:
            return "admin", faculty
        if faculty.is_hod:
            return "hod", faculty
        return "faculty", faculty
    return None, None


# ---------------------------------------------------------------------------
# Current-user dependency
# ---------------------------------------------------------------------------

def get_current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        email = payload["sub"]
        role = payload["role"]
        uid = int(payload["uid"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token") from None

    if role == "student":
        user = db.get(Student, uid)
    elif role in {"faculty", "admin", "hod"}:
        user = db.get(Faculty, uid)
    else:
        user = None

    if not user or user.email != email or user.status != AccountStatus.active.value:
        raise HTTPException(status_code=401, detail="inactive_or_missing_user")
    return {"role": role, "user": user}


def require_role(*roles: Literal["student", "faculty", "admin", "hod"]):
    """Dependency that checks the user has one of the allowed roles.

    Admin can access everything. HOD can access hod + faculty endpoints.
    """

    def dependency(current=Depends(get_current_user)):
        effective_role = current["role"]
        # Admin inherits all roles
        if effective_role == "admin":
            return current
        # HOD inherits faculty role
        if effective_role == "hod" and "faculty" in roles:
            return current
        if effective_role not in roles:
            raise HTTPException(status_code=403, detail="insufficient_role")
        return current

    return dependency
