"""Pydantic schemas for Course, Teacher listing, and Enrollment Management."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TeacherCreate(BaseModel):
    """Payload for an Admin to register a new teacher."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=120)
    password: str = Field(..., min_length=6, max_length=128)
    employee_id: str = Field(..., min_length=3, max_length=30)
    department: str = Field(..., min_length=2, max_length=80)
    designation: str = Field("Lecturer", min_length=2, max_length=80)


class TeacherResponse(BaseModel):
    """Serialized teacher summary."""

    id: int
    user_id: int
    username: str
    email: str
    full_name: str
    employee_id: str
    department: str
    designation: str

    model_config = ConfigDict(from_attributes=True)


class CourseCreate(BaseModel):
    """Payload to create a course."""

    course_code: str = Field(..., min_length=3, max_length=20)
    title: str = Field(..., min_length=2, max_length=150)
    credits: float = Field(..., gt=0, le=10.0)
    semester: int = Field(..., ge=1, le=12)
    department: str = Field("CSE", min_length=2, max_length=80)
    teacher_id: int | None = None


class CourseUpdate(BaseModel):
    """Payload to update an existing course."""

    title: str | None = Field(default=None, min_length=2, max_length=150)
    credits: float | None = Field(default=None, gt=0, le=10.0)
    semester: int | None = Field(default=None, ge=1, le=12)
    department: str | None = Field(default=None, min_length=2, max_length=80)
    teacher_id: int | None = None


class CourseResponse(BaseModel):
    """Serialized course output including optional assigned teacher name."""

    id: int
    course_code: str
    title: str
    credits: float
    semester: int
    department: str
    teacher_id: int | None = None
    teacher_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class EnrollmentRequest(BaseModel):
    """Optional student_id when Admin enrolls a student; omitted for student self-enrollment."""

    student_id: int | None = None


class EnrollmentResponse(BaseModel):
    """Serialized course enrollment confirmation."""

    id: int
    student_id: int
    course_id: int
    enrolled_at: datetime

    model_config = ConfigDict(from_attributes=True)
