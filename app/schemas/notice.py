"""Pydantic schemas for Notices and Notifications."""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class NoticeCreate(BaseModel):
    """Payload to publish an academic notice."""

    title: str = Field(..., min_length=3, max_length=200)
    content: str = Field(..., min_length=3, max_length=5000)
    target_role: Literal["all", "student", "teacher"] = "all"
    course_id: int | None = None


class NoticeResponse(BaseModel):
    """Serialized academic announcement."""

    id: int
    title: str
    content: str
    target_role: str
    course_id: int | None = None
    course_code: str | None = None
    author_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationResponse(BaseModel):
    """Serialized user notification generated via Observer/Factory/Adapter."""

    id: int
    user_id: int
    channel: str
    subject: str
    message: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
