"""Pydantic schemas for Student Management."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StudentCreate(BaseModel):
    """Payload to register a new student user and academic profile."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=120)
    password: str = Field(..., min_length=6, max_length=128)
    roll_number: str = Field(..., min_length=3, max_length=30)
    department: str = Field(..., min_length=2, max_length=80)
    batch_year: int = Field(..., ge=2000, le=2100)
    current_semester: int = Field(1, ge=1, le=12)
    phone: str | None = Field(default=None, max_length=30)


class StudentUpdate(BaseModel):
    """Payload to update an existing student profile and account metadata."""

    email: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    department: str | None = Field(default=None, min_length=2, max_length=80)
    batch_year: int | None = Field(default=None, ge=2000, le=2100)
    current_semester: int | None = Field(default=None, ge=1, le=12)
    phone: str | None = Field(default=None, max_length=30)
    is_active: bool | None = None


class StudentResponse(BaseModel):
    """Serialized student representation combining user and profile fields."""

    id: int
    user_id: int
    username: str
    email: str
    full_name: str
    is_active: bool
    roll_number: str
    department: str
    batch_year: int
    current_semester: int
    phone: str | None = None

    model_config = ConfigDict(from_attributes=True)
