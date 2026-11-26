"""Notice and Notification ORM models."""

from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Notice(Base):
    """Academic announcement published by Admins or Teachers."""

    __tablename__ = "notices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    target_role: Mapped[str] = mapped_column(String(20), nullable=False, default="all")
    course_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True
    )
    author_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    author = relationship("User", lazy="joined")
    course = relationship("Course", lazy="joined")


class Notification(Base):
    """Persisted notification delivered to a user via Factory/Adapter/Observer."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="in_app")
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utc_now, nullable=False)

    user = relationship("User", lazy="joined")
