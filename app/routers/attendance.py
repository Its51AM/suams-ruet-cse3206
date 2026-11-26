"""Attendance Management API endpoints."""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_roles
from app.models.attendance import AttendanceRecord
from app.models.course import Course
from app.models.user import Teacher, User, UserRole
from app.schemas.attendance import (
    AttendanceBatchRequest,
    AttendanceRecordResponse,
    StudentAttendanceSummary,
)
from app.services.attendance_service import AttendanceService
from app.services.student_service import StudentService

router = APIRouter(prefix="/api/attendance", tags=["Attendance"])


def _to_response(record: AttendanceRecord) -> AttendanceRecordResponse:
    return AttendanceRecordResponse(
        id=record.id,
        student_id=record.student_id,
        student_name=record.student.user.full_name if record.student and record.student.user else "",
        roll_number=record.student.roll_number if record.student else "",
        course_id=record.course_id,
        course_code=record.course.course_code if record.course else "",
        attendance_date=record.attendance_date,
        status=record.status,
    )


def _assert_teacher_owns_course(db: Session, user: User, course_id: int) -> None:
    if user.role != UserRole.TEACHER.value:
        return
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
    teacher = db.query(Teacher).filter(Teacher.user_id == user.id).first()
    if not teacher or course.teacher_id != teacher.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teachers may only manage attendance for their assigned courses.",
        )


@router.post("/courses/{course_id}", response_model=list[AttendanceRecordResponse])
def mark_course_attendance(
    course_id: int,
    payload: AttendanceBatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """Record or update attendance for enrolled students in a course."""
    _assert_teacher_owns_course(db, current_user, course_id)
    try:
        records = AttendanceService.record_attendance(
            db,
            course_id=course_id,
            attendance_date=payload.attendance_date,
            entries=payload.entries,
            marked_by_user_id=current_user.id,
        )
        return [_to_response(r) for r in records]
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/courses/{course_id}", response_model=list[AttendanceRecordResponse])
def view_course_attendance(
    course_id: int,
    attendance_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """View attendance records for a course (Admin or assigned Teacher)."""
    _assert_teacher_owns_course(db, current_user, course_id)
    records = AttendanceService.get_course_attendance(db, course_id, attendance_date=attendance_date)
    return [_to_response(r) for r in records]


@router.get("/my", response_model=StudentAttendanceSummary)
def view_my_attendance(
    course_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
):
    """Student views their own attendance summary and records."""
    student = StudentService.get_student_by_user_id(db, current_user.id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found.")
    summary = AttendanceService.get_student_attendance_summary(db, student.id, course_id=course_id)
    return StudentAttendanceSummary(
        student_id=summary["student_id"],
        total_classes=summary["total_classes"],
        present_count=summary["present_count"],
        late_count=summary["late_count"],
        absent_count=summary["absent_count"],
        attendance_percentage=summary["attendance_percentage"],
        records=[_to_response(r) for r in summary["records"]],
    )
