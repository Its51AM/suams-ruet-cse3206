"""Pydantic schemas for authentication and user identity."""

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """Credentials payload for user authentication."""

    identifier: str = Field(..., min_length=2, max_length=120, description="Username or email")
    password: str = Field(..., min_length=1, max_length=128)


class UserResponse(BaseModel):
    """Public representation of an authenticated user."""

    id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Authentication response metadata."""

    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    full_name: str
