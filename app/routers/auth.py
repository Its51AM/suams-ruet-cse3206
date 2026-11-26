"""Authentication and RBAC API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    COOKIE_NAME,
    create_access_token,
    get_current_user,
    require_roles,
)
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Authenticate user credentials and issue an HttpOnly JWT cookie."""
    user = AuthService.authenticate_user(db, payload.identifier, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password.",
        )

    settings = get_settings()
    token = create_access_token({"sub": user.username, "role": user.role})
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.access_token_expire_minutes * 60,
    )
    return TokenResponse(
        access_token=token,
        role=user.role,
        username=user.username,
        full_name=user.full_name,
    )


@router.post("/logout")
def logout(response: Response):
    """Clear the active authentication session cookie."""
    response.delete_cookie(key=COOKIE_NAME)
    return {"message": "Logged out successfully."}


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return current_user


@router.get("/admin-check")
def admin_only_check(current_user: User = Depends(require_roles(UserRole.ADMIN))):
    """Protected endpoint verifying admin RBAC enforcement."""
    return {"status": "ok", "role": current_user.role}
