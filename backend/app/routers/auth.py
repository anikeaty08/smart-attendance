from datetime import timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import FirstLoginVerification
from app.otp import generate_otp, hash_otp, send_otp_email, verify_otp
from app.schemas import FirstLoginOtpStartResponse, FirstLoginOtpVerifyRequest, FirstLoginOtpVerifyResponse, MeResponse
from app.security import require_role
from app.time_utils import as_utc, utcnow

router = APIRouter(tags=["Auth"])


def _verification_for(db: Session, email: str) -> FirstLoginVerification:
    verification = db.scalar(select(FirstLoginVerification).where(FirstLoginVerification.email == email))
    if not verification:
        verification = FirstLoginVerification(email=email, verified=False, attempts=0)
        db.add(verification)
        db.flush()
    return verification


def _clerk_user_id(email: str) -> str | None:
    if not settings.clerk_secret_key:
        return None
    response = httpx.get(
        "https://api.clerk.com/v1/users",
        params={"email_address": email},
        headers={"Authorization": f"Bearer {settings.clerk_secret_key}"},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if isinstance(data, list) and data:
        return data[0]["id"]
    return None


def _clear_clerk_first_login_flag(email: str) -> None:
    user_id = _clerk_user_id(email)
    if not user_id:
        return
    response = httpx.patch(
        f"https://api.clerk.com/v1/users/{user_id}/metadata",
        headers={"Authorization": f"Bearer {settings.clerk_secret_key}", "Content-Type": "application/json"},
        json={"public_metadata": {"must_change_password": False, "first_login_verified": True}},
        timeout=30,
    )
    response.raise_for_status()


def _must_change_password(user) -> bool:
    return True


@router.get("/me", response_model=MeResponse)
def me(current=Depends(require_role("student", "faculty", "admin", "hod")), db: Session = Depends(get_db)):
    """Return current user's profile. Authentication is handled by Clerk on the frontend.
    The backend only reads the Clerk JWT to identify who the user is in our database."""
    user = current["user"]
    dept = getattr(user, "department", None) or getattr(user, "branch", None)
    verification = _verification_for(db, user.email)
    db.commit()
    return MeResponse(
        id=user.id,
        role=current["role"],
        email=user.email,
        name=user.name,
        is_admin=bool(getattr(user, "is_admin", False)),
        is_hod=bool(getattr(user, "is_hod", False)),
        department_id=getattr(user, "department_id", None) or getattr(user, "branch_id", None),
        department_name=dept.name if dept else None,
        first_login_verified=verification.verified,
        must_change_password=not verification.verified,
    )


@router.post("/auth/first-login/start", response_model=FirstLoginOtpStartResponse)
def start_first_login_otp(
    current=Depends(require_role("student", "faculty", "admin", "hod")),
    db: Session = Depends(get_db),
):
    user = current["user"]
    verification = _verification_for(db, user.email)
    if verification.verified:
        return FirstLoginOtpStartResponse(
            status="already_verified",
            email=user.email,
            expires_in_minutes=settings.first_login_otp_minutes,
            delivery="none",
        )

    otp = generate_otp()
    verification.otp_hash = hash_otp(otp)
    verification.expires_at = utcnow() + timedelta(minutes=settings.first_login_otp_minutes)
    verification.attempts = 0
    delivery = send_otp_email(user.email, otp)
    db.commit()
    return FirstLoginOtpStartResponse(
        status="sent",
        email=user.email,
        expires_in_minutes=settings.first_login_otp_minutes,
        delivery=delivery,
    )


@router.post("/auth/first-login/verify", response_model=FirstLoginOtpVerifyResponse)
def verify_first_login_otp(
    payload: FirstLoginOtpVerifyRequest,
    current=Depends(require_role("student", "faculty", "admin", "hod")),
    db: Session = Depends(get_db),
):
    user = current["user"]
    verification = _verification_for(db, user.email)
    if verification.verified:
        return FirstLoginOtpVerifyResponse(status="already_verified", first_login_verified=True)
    if verification.attempts >= 5:
        raise HTTPException(status_code=423, detail="first_login_otp_locked")
    if not verification.expires_at or as_utc(verification.expires_at) < utcnow():
        raise HTTPException(status_code=400, detail="first_login_otp_expired")
    verification.attempts += 1
    if not verify_otp(payload.otp, verification.otp_hash):
        db.commit()
        raise HTTPException(status_code=400, detail="invalid_first_login_otp")

    verification.verified = True
    verification.verified_at = utcnow()
    verification.otp_hash = None
    db.commit()
    try:
        _clear_clerk_first_login_flag(user.email)
    except Exception:
        pass
    return FirstLoginOtpVerifyResponse(status="verified", first_login_verified=True)
