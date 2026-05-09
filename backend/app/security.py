from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import secrets
from typing import Literal

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import AccountStatus, Faculty, Student

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/google")
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


def create_access_token(subject: str, role: str, user_id: int) -> str:
    expires = datetime.now(UTC) + timedelta(minutes=settings.access_token_minutes)
    payload = {"sub": subject, "role": role, "uid": user_id, "exp": expires}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _domain(email: str) -> str:
    return email.split("@", 1)[1].lower()


def validate_allowed_domain(email: str) -> None:
    domain = _domain(email)
    if domain not in settings.student_domains and domain not in settings.staff_domains:
        raise HTTPException(status_code=403, detail="email_domain_not_allowed")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        email = payload["sub"]
        role = payload["role"]
        uid = int(payload["uid"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token") from None

    if role == "student":
        user = db.get(Student, uid)
    elif role in {"faculty", "admin"}:
        user = db.get(Faculty, uid)
    else:
        user = None

    if not user or user.email != email or user.status != AccountStatus.active.value:
        raise HTTPException(status_code=401, detail="inactive_or_missing_user")
    return {"role": role, "user": user}


def require_role(*roles: Literal["student", "faculty", "admin"]):
    def dependency(current=Depends(get_current_user)):
        if current["role"] not in roles:
            raise HTTPException(status_code=403, detail="insufficient_role")
        return current

    return dependency


def find_user_by_email(db: Session, email: str):
    student = db.scalar(select(Student).where(Student.email == email.lower()))
    if student:
        return "student", student
    faculty = db.scalar(select(Faculty).where(Faculty.email == email.lower()))
    if faculty and faculty.is_admin:
        return "admin", faculty
    if faculty:
        return "faculty", faculty
    return None, None
