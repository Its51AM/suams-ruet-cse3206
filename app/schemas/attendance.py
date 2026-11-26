"""Pydantic schemas for Attendance Management."""

from datetime import date
from pydantic import BaseModel, ConfigDict, Field
from app.models.attendance import AttendanceStatus


class AttendanceEntry(BaseModel):
    """Single student attendance decision."""

    student_id: int
    status: AttendanceStatus


class AttendanceBatchRequest(BaseModel):
    """Batch attendance payload for a course on a given date."""

    attendance_date: date
    entries: list[AttendanceEntry] = Field(..., min_length=1)


class AttendanceRecordResponse(BaseModel):
    """Serialized attendance record."""

    id: int
    student_id: int
    student_name: str
    roll_number: str
    course_id: int
    course_code: str
    attendance_date: date
    status: str

    model_config = ConfigDict(from_attributes=True)


class StudentAttendanceSummary(BaseModel):
    """Aggregated attendance statistics and history for a student."""

    student_id: int
    total_classes: int
    present_count: int
    late_count: int
    absent_count: int
    attendance_percentage: float
    records: list[AttendanceRecordResponse]
