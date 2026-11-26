"""Security utilities: password hashing, JWT tokens, and RBAC dependencies."""

from datetime import datetime, timedelta, timezone
from typing import Callable
import bcrypt
from fastapi import Depends, HTTPException, Request, status
import jwt
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User, UserRole

COOKIE_NAME = "suams_access_token"


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt with a fresh salt."""
    password_bytes = plain_password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash."""
    if not plain_password or not password_hash:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    settings = get_settings()
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication credentials.",
        ) from exc


def extract_token_from_request(request: Request) -> str | None:
    """Extract JWT from Authorization Bearer header or HTTP-only session cookie."""
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return request.cookies.get(COOKIE_NAME)


def _resolve_user_from_token(token: str, db: Session) -> User | None:
    payload = decode_access_token(token)
    subject = payload.get("sub")
    if not subject:
        return None
    return (
        db.query(User)
        .filter(or_(User.username == subject, User.email == subject))
        .first()
    )


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """FastAPI dependency returning the authenticated active user or raising 401."""
    token = extract_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    user = _resolve_user_from_token(token, db)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or inactive.",
        )
    return user


def get_optional_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Return authenticated user if valid cookie/header exists, else None."""
    token = extract_token_from_request(request)
    if not token:
        return None
    try:
        user = _resolve_user_from_token(token, db)
    except HTTPException:
        return None
    if not user or not user.is_active:
        return None
    return user


def require_roles(*allowed_roles: UserRole) -> Callable[[User], User]:
    """Build a FastAPI dependency enforcing role-based access control."""
    allowed_values = {role.value for role in allowed_roles}

    def role_dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return current_user

    return role_dependency
