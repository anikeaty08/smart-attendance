from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import AccountStatus, Faculty
from app.schemas import (
    ChangePasswordRequest,
    GoogleLoginRequest,
    MeResponse,
    TokenResponse,
    WebLoginRequest,
)
from app.security import (
    create_access_token,
    find_user_by_email,
    hash_password,
    require_role,
    validate_allowed_domain,
    verify_password,
)
from app.utils import normalize_email

router = APIRouter(tags=["Auth"])


@router.post("/auth/google", response_model=TokenResponse)
def google_login(payload: GoogleLoginRequest, db: Session = Depends(get_db)):
    email: str | None = None
    if settings.google_client_id and payload.id_token:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token

        try:
            claims = id_token.verify_oauth2_token(
                payload.id_token,
                google_requests.Request(),
                settings.google_client_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=401, detail="invalid_google_token") from exc
        if not claims.get("email_verified"):
            raise HTTPException(status_code=403, detail="google_email_not_verified")
        email = claims.get("email")
    elif payload.email:
        # Local dev mode: accept email directly
        email = str(payload.email)
    else:
        raise HTTPException(status_code=400, detail="email_required_for_local_login")

    email = normalize_email(email)
    validate_allowed_domain(email)
    role, user = find_user_by_email(db, email)
    if not user or user.status != AccountStatus.active.value:
        raise HTTPException(status_code=403, detail="user_not_registered_or_inactive")
    token = create_access_token(user.email, role, user.id)
    return TokenResponse(access_token=token, role=role, email=user.email, name=user.name)


@router.post("/auth/web-login", response_model=TokenResponse)
def web_login(payload: WebLoginRequest, db: Session = Depends(get_db)):
    """Email + password login for admin/HOD web panel."""
    email = normalize_email(str(payload.email))
    validate_allowed_domain(email)
    role, user = find_user_by_email(db, email)
    if not user or not isinstance(user, Faculty):
        raise HTTPException(status_code=401, detail="invalid_credentials")
    if user.status != AccountStatus.active.value:
        raise HTTPException(status_code=403, detail="account_inactive")
    if not user.password_hash:
        raise HTTPException(status_code=401, detail="password_not_set")
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid_credentials")
    token = create_access_token(user.email, role, user.id)
    return TokenResponse(access_token=token, role=role, email=user.email, name=user.name)


@router.get("/me", response_model=MeResponse)
def me(current=Depends(require_role("student", "faculty", "admin", "hod"))):
    user = current["user"]
    dept = getattr(user, "department", None) or getattr(user, "branch", None)
    return MeResponse(
        id=user.id,
        role=current["role"],
        email=user.email,
        name=user.name,
        is_admin=bool(getattr(user, "is_admin", False)),
        is_hod=bool(getattr(user, "is_hod", False)),
        department_id=getattr(user, "department_id", None) or getattr(user, "branch_id", None),
        department_name=dept.name if dept else None,
    )


@router.put("/me/password")
def change_password(
    payload: ChangePasswordRequest,
    current=Depends(require_role("admin", "hod", "faculty")),
    db: Session = Depends(get_db),
):
    user: Faculty = current["user"]
    if user.password_hash and not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="old_password_incorrect")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"status": "password_updated"}
