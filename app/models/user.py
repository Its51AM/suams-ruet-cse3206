"""User, Student, and Teacher ORM models."""

from datetime import datetime, timezone
import enum
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class UserRole(str, enum.Enum):
    """Supported RBAC roles within SUAMS."""

    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """Core authentication and identity entity."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    student_profile: Mapped["Student | None"] = relationship(
        "Student", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    teacher_profile: Mapped["Teacher | None"] = relationship(
        "Teacher", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class Student(Base):
    """Student academic profile linked 1-to-1 with a User."""

    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    roll_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(80), nullable=False)
    batch_year: Mapped[int] = mapped_column(Integer, nullable=False)
    current_semester: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="student_profile")


class Teacher(Base):
    """Teacher profile linked 1-to-1 with a User."""

    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    employee_id: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(80), nullable=False)
    designation: Mapped[str] = mapped_column(String(80), default="Lecturer", nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="teacher_profile")
