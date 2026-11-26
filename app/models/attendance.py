"""Attendance ORM model."""

from datetime import date, datetime, timezone
import enum
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class AttendanceStatus(str, enum.Enum):
    """Valid daily attendance statuses."""

    PRESENT = "Present"
    ABSENT = "Absent"
    LATE = "Late"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AttendanceRecord(Base):
    """Daily attendance status for a student in a specific course."""

    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", "attendance_date", name="uq_attendance_day"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    marked_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    student = relationship("Student", lazy="joined")
    course = relationship("Course", lazy="joined")
