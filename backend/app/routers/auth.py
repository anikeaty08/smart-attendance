from fastapi import APIRouter, Depends

from app.schemas import MeResponse
from app.security import require_role

router = APIRouter(tags=["Auth"])


@router.get("/me", response_model=MeResponse)
def me(current=Depends(require_role("student", "faculty", "admin", "hod"))):
    """Return current user's profile. Authentication is handled by Clerk on the frontend.
    The backend only reads the Clerk JWT to identify who the user is in our database."""
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
