"""Course and Enrollment ORM models."""

from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Course(Base):
    """University course offered in a specific semester and department."""

    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    course_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    credits: Mapped[float] = mapped_column(Float, nullable=False, default=3.0)
    semester: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    department: Mapped[str] = mapped_column(String(80), nullable=False, default="CSE")
    teacher_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("teachers.id", ondelete="SET NULL"), nullable=True
    )

    teacher = relationship("Teacher", lazy="joined")
    enrollments = relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")


class Enrollment(Base):
    """Many-to-many association between Student and Course."""

    __tablename__ = "enrollments"
    __table_args__ = (UniqueConstraint("student_id", "course_id", name="uq_student_course"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    student = relationship("Student", lazy="joined")
    course = relationship("Course", back_populates="enrollments")
