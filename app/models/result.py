"""Result and Grade ORM model."""

from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Result(Base):
    """Published assessment marks and computed grade for a student in a course."""

    __tablename__ = "results"
    __table_args__ = (UniqueConstraint("student_id", "course_id", name="uq_result_student_course"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    marks: Mapped[float] = mapped_column(Float, nullable=False)
    letter_grade: Mapped[str] = mapped_column(String(5), nullable=False)
    grade_point: Mapped[float] = mapped_column(Float, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    student = relationship("Student", lazy="joined")
    course = relationship("Course", lazy="joined")
