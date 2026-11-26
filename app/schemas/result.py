"""Pydantic schemas for Result and Grade Management."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ResultPublishRequest(BaseModel):
    """Payload for publishing or updating a student's course marks."""

    student_id: int
    course_id: int
    marks: float = Field(..., ge=0.0, le=100.0)


class ResultResponse(BaseModel):
    """Serialized course result with computed letter grade and grade point."""

    id: int
    student_id: int
    student_name: str
    roll_number: str
    course_id: int
    course_code: str
    course_title: str
    credits: float
    marks: float
    letter_grade: str
    grade_point: float
    published_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentTranscriptResponse(BaseModel):
    """Complete student grade sheet and weighted GPA."""

    student_id: int
    total_credits: float
    gpa: float
    results: list[ResultResponse]
