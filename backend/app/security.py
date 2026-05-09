import hashlib
import hmac
import secrets
from functools import lru_cache
from typing import Literal

import httpx
import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import AccountStatus, Faculty, Student

bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Clerk JWKS — fetched once and cached
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_jwks() -> dict:
    """Fetch Clerk's public JWKS. Cached for the process lifetime."""
    url = settings.clerk_jwks_url
    if not url:
        raise RuntimeError("Clerk JWKS URL could not be derived from publishable key.")
    resp = httpx.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _verify_clerk_token(token: str) -> dict:
    """Verify a Clerk session token and return the payload."""
    jwks = _get_jwks()
    try:
        # pyjwt will pick the right key from the JWKS automatically
        payload = pyjwt.decode(
            token,
            pyjwt.PyJWKClient(settings.clerk_jwks_url).get_signing_key_from_jwt(token).key,
            algorithms=["RS256"],
            options={"verify_aud": False},  # Clerk tokens don't use aud by default
        )
        return payload
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token_expired")
    except pyjwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"invalid_token: {exc}")


# ---------------------------------------------------------------------------
# Session code hashing (4-digit attendance code — unchanged)
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
# Domain validation
# ---------------------------------------------------------------------------

def validate_allowed_domain(email: str) -> None:
    domain = email.split("@", 1)[1].lower()
    if domain not in settings.domains:
        raise HTTPException(status_code=403, detail="email_domain_not_allowed")


# ---------------------------------------------------------------------------
# Role detection from DB
# ---------------------------------------------------------------------------

def find_user_by_email(db: Session, email: str):
    """Return (role, user) by looking up email in students then faculty."""
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
# FastAPI dependency — verifies Clerk JWT, returns {role, user}
# ---------------------------------------------------------------------------

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")

    payload = _verify_clerk_token(credentials.credentials)

    # Clerk stores email in primary_email_address or email_addresses[0].email_address
    # The session token typically exposes it under the "email" or nested claim.
    # Standard Clerk JWT structure uses sub = user_id; email comes from custom claims or
    # must be fetched. However with Clerk's "email" custom claim or via the /me endpoint.
    # We use the email claim we configure in Clerk's session token customization.
    email = payload.get("email")
    if not email:
        # Fallback: try extracting from email_addresses if present
        email_addresses = payload.get("email_addresses", [])
        if email_addresses:
            email = email_addresses[0].get("email_address")
    if not email:
        raise HTTPException(status_code=401, detail="email_claim_missing_in_token")

    email = email.strip().lower()
    validate_allowed_domain(email)

    role, user = find_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=403, detail="user_not_registered")
    if user.status != AccountStatus.active.value:
        raise HTTPException(status_code=403, detail="account_inactive")

    return {"role": role, "user": user}


def require_role(*roles: Literal["student", "faculty", "admin", "hod"]):
    """Role-based access control with inheritance: admin > hod > faculty."""

    def dependency(current=Depends(get_current_user)):
        effective_role = current["role"]
        # Admin inherits everything
        if effective_role == "admin":
            return current
        # HOD inherits faculty access
        if effective_role == "hod" and "faculty" in roles:
            return current
        if effective_role not in roles:
            raise HTTPException(status_code=403, detail="insufficient_role")
        return current

    return dependency
