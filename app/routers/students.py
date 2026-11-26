"""Student Management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.user import Student, User, UserRole
from app.schemas.student import StudentCreate, StudentResponse, StudentUpdate
from app.services.student_service import StudentService

router = APIRouter(prefix="/api/students", tags=["Students"])


def _to_response(student: Student) -> StudentResponse:
    return StudentResponse(
        id=student.id,
        user_id=student.user_id,
        username=student.user.username,
        email=student.user.email,
        full_name=student.user.full_name,
        is_active=student.user.is_active,
        roll_number=student.roll_number,
        department=student.department,
        batch_year=student.batch_year,
        current_semester=student.current_semester,
        phone=student.phone,
    )


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: StudentCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Create a new student account and academic profile (Admin only)."""
    try:
        student = StudentService.create_student(db, payload)
        return _to_response(student)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=list[StudentResponse])
def list_students(
    department: str | None = Query(default=None),
    semester: int | None = Query(default=None, ge=1, le=12),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _staff: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """List students with optional filtering (Admin & Teacher)."""
    students = StudentService.list_students(
        db, department=department, semester=semester, search=search
    )
    return [_to_response(s) for s in students]


@router.get("/me", response_model=StudentResponse)
def get_my_student_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
):
    """Return the authenticated student's own profile."""
    student = StudentService.get_student_by_user_id(db, current_user.id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found.")
    return _to_response(student)


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve a student profile (Admin, Teacher, or owning Student)."""
    student = StudentService.get_student_by_id(db, student_id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")
    if current_user.role == UserRole.STUDENT.value and student.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students may only view their own profile.",
        )
    return _to_response(student)


@router.put("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: int,
    payload: StudentUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Update a student record (Admin only)."""
    try:
        student = StudentService.update_student(db, student_id, payload)
        return _to_response(student)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/{student_id}")
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Delete a student record (Admin only)."""
    deleted = StudentService.delete_student(db, student_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found.")
    return {"message": "Student deleted successfully."}
