"""Result and Grade Management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_roles
from app.models.course import Course
from app.models.result import Result
from app.models.user import Teacher, User, UserRole
from app.patterns.observer import build_default_publisher
from app.schemas.result import (
    ResultPublishRequest,
    ResultResponse,
    StudentTranscriptResponse,
)
from app.services.result_service import ResultService
from app.services.student_service import StudentService

router = APIRouter(prefix="/api/results", tags=["Results"])


def _to_response(result: Result) -> ResultResponse:
    return ResultResponse(
        id=result.id,
        student_id=result.student_id,
        student_name=result.student.user.full_name if result.student and result.student.user else "",
        roll_number=result.student.roll_number if result.student else "",
        course_id=result.course_id,
        course_code=result.course.course_code if result.course else "",
        course_title=result.course.title if result.course else "",
        credits=result.course.credits if result.course else 0.0,
        marks=result.marks,
        letter_grade=result.letter_grade,
        grade_point=result.grade_point,
        published_at=result.published_at,
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
            detail="Teachers may only publish or view results for their assigned courses.",
        )


@router.post("", response_model=ResultResponse)
def publish_result(
    payload: ResultPublishRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """Publish or update student marks and trigger Observer notifications."""
    _assert_teacher_owns_course(db, current_user, payload.course_id)
    try:
        publisher = build_default_publisher()
        result = ResultService.publish_result(
            db,
            student_id=payload.student_id,
            course_id=payload.course_id,
            marks=payload.marks,
            publisher=publisher,
        )
        return _to_response(result)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/my", response_model=StudentTranscriptResponse)
def view_my_results(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
):
    """Return the authenticated student's published results and calculated GPA."""
    student = StudentService.get_student_by_user_id(db, current_user.id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found.")
    transcript = ResultService.get_student_transcript(db, student.id)
    return StudentTranscriptResponse(
        student_id=transcript["student_id"],
        total_credits=transcript["total_credits"],
        gpa=transcript["gpa"],
        results=[_to_response(r) for r in transcript["results"]],
    )


@router.get("/courses/{course_id}", response_model=list[ResultResponse])
def view_course_results(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """List published results for a course (Admin or assigned Teacher)."""
    _assert_teacher_owns_course(db, current_user, course_id)
    results = ResultService.get_course_results(db, course_id)
    return [_to_response(r) for r in results]
