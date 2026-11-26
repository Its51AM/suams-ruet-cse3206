"""Course, Teacher, and Enrollment API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.course import Course
from app.models.user import Teacher, User, UserRole
from app.routers.students import _to_response as student_to_response
from app.schemas.course import (
    CourseCreate,
    CourseResponse,
    CourseUpdate,
    EnrollmentRequest,
    EnrollmentResponse,
    TeacherCreate,
    TeacherResponse,
)
from app.schemas.student import StudentResponse
from app.services.course_service import CourseService
from app.services.student_service import StudentService

router = APIRouter(prefix="/api/courses", tags=["Courses"])


def _course_to_response(course: Course) -> CourseResponse:
    teacher_name = None
    if course.teacher and course.teacher.user:
        teacher_name = course.teacher.user.full_name
    return CourseResponse(
        id=course.id,
        course_code=course.course_code,
        title=course.title,
        credits=course.credits,
        semester=course.semester,
        department=course.department,
        teacher_id=course.teacher_id,
        teacher_name=teacher_name,
    )


def _teacher_to_response(teacher: Teacher) -> TeacherResponse:
    return TeacherResponse(
        id=teacher.id,
        user_id=teacher.user_id,
        username=teacher.user.username,
        email=teacher.user.email,
        full_name=teacher.user.full_name,
        employee_id=teacher.employee_id,
        department=teacher.department,
        designation=teacher.designation,
    )


@router.post("/teachers", response_model=TeacherResponse, status_code=status.HTTP_201_CREATED)
def create_teacher(
    payload: TeacherCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Register a new teacher account (Admin only)."""
    try:
        teacher = CourseService.create_teacher(db, payload)
        return _teacher_to_response(teacher)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/teachers", response_model=list[TeacherResponse])
def list_teachers(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """List all teachers."""
    return [_teacher_to_response(t) for t in CourseService.list_teachers(db)]


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Create a new course (Admin only)."""
    try:
        course = CourseService.create_course(db, payload)
        return _course_to_response(course)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=list[CourseResponse])
def list_courses(
    semester: int | None = Query(default=None, ge=1, le=12),
    department: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """List all courses with optional semester or department filter."""
    courses = CourseService.list_courses(db, semester=semester, department=department)
    return [_course_to_response(c) for c in courses]


@router.get("/my", response_model=list[CourseResponse])
def list_my_courses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return courses relevant to the logged-in teacher or student."""
    if current_user.role == UserRole.TEACHER.value:
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        if not teacher:
            return []
        return [_course_to_response(c) for c in CourseService.list_courses(db, teacher_id=teacher.id)]
    if current_user.role == UserRole.STUDENT.value:
        student = StudentService.get_student_by_user_id(db, current_user.id)
        if not student:
            return []
        return [_course_to_response(c) for c in CourseService.list_student_courses(db, student.id)]
    return [_course_to_response(c) for c in CourseService.list_courses(db)]


@router.put("/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: int,
    payload: CourseUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Update course details or assigned teacher (Admin only)."""
    try:
        course = CourseService.update_course(db, course_id, payload)
        return _course_to_response(course)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{course_id}")
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Delete a course (Admin only)."""
    if not CourseService.delete_course(db, course_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
    return {"message": "Course deleted successfully."}


@router.post("/{course_id}/enroll", response_model=EnrollmentResponse, status_code=status.HTTP_201_CREATED)
def enroll_in_course(
    course_id: int,
    payload: EnrollmentRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.STUDENT)),
):
    """Register a student in a course (Student self-enrollment or Admin assignment)."""
    target_student_id: int | None = payload.student_id if payload else None
    if current_user.role == UserRole.STUDENT.value:
        student = StudentService.get_student_by_user_id(db, current_user.id)
        if not student:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found.")
        target_student_id = student.id
    elif target_student_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="student_id is required when an Admin enrolls a student.",
        )

    try:
        return CourseService.enroll_student(db, course_id=course_id, student_id=target_student_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{course_id}/students", response_model=list[StudentResponse])
def list_enrolled_students(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """List students enrolled in a course (Admin or assigned Teacher)."""
    course = CourseService.get_course_by_id(db, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
    if current_user.role == UserRole.TEACHER.value:
        teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
        if not teacher or course.teacher_id != teacher.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teachers can only view rosters for their assigned courses.",
            )
    students = CourseService.list_course_students(db, course_id)
    return [student_to_response(s) for s in students]
