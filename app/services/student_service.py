"""Business logic for Student Management."""

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload
from app.core.security import hash_password
from app.models.user import Student, User, UserRole
from app.schemas.student import StudentCreate, StudentUpdate


class StudentService:
    """Service handling student CRUD and profile lookup operations."""

    @staticmethod
    def create_student(db: Session, payload: StudentCreate) -> Student:
        """Create a User (student role) and linked Student profile atomically."""
        clean_username = payload.username.strip()
        clean_email = str(payload.email).strip().lower()
        clean_roll = payload.roll_number.strip()

        existing_user = (
            db.query(User)
            .filter(or_(User.username == clean_username, User.email == clean_email))
            .first()
        )
        if existing_user:
            raise ValueError("A user with this username or email already exists.")

        existing_roll = db.query(Student).filter(Student.roll_number == clean_roll).first()
        if existing_roll:
            raise ValueError("A student with this roll number already exists.")

        user = User(
            username=clean_username,
            email=clean_email,
            full_name=payload.full_name.strip(),
            password_hash=hash_password(payload.password),
            role=UserRole.STUDENT.value,
            is_active=True,
        )
        db.add(user)
        db.flush()

        student = Student(
            user_id=user.id,
            roll_number=clean_roll,
            department=payload.department.strip(),
            batch_year=payload.batch_year,
            current_semester=payload.current_semester,
            phone=payload.phone.strip() if payload.phone else None,
        )
        db.add(student)
        db.commit()
        db.refresh(student)
        return student

    @staticmethod
    def list_students(
        db: Session,
        *,
        department: str | None = None,
        semester: int | None = None,
        search: str | None = None,
    ) -> list[Student]:
        """List students with optional department, semester, and keyword filters."""
        query = db.query(Student).join(User).options(joinedload(Student.user))
        if department:
            query = query.filter(Student.department.ilike(department.strip()))
        if semester is not None:
            query = query.filter(Student.current_semester == semester)
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Student.roll_number.ilike(term),
                    User.full_name.ilike(term),
                    User.email.ilike(term),
                )
            )
        return query.order_by(Student.roll_number.asc()).all()

    @staticmethod
    def get_student_by_id(db: Session, student_id: int) -> Student | None:
        """Fetch a single student by primary key."""
        return (
            db.query(Student)
            .options(joinedload(Student.user))
            .filter(Student.id == student_id)
            .first()
        )

    @staticmethod
    def get_student_by_user_id(db: Session, user_id: int) -> Student | None:
        """Fetch a student profile by linked user_id."""
        return (
            db.query(Student)
            .options(joinedload(Student.user))
            .filter(Student.user_id == user_id)
            .first()
        )

    @staticmethod
    def update_student(db: Session, student_id: int, payload: StudentUpdate) -> Student:
        """Update student profile and associated user metadata."""
        student = StudentService.get_student_by_id(db, student_id)
        if not student:
            raise LookupError("Student not found.")

        if payload.email is not None:
            clean_email = str(payload.email).strip().lower()
            duplicate = (
                db.query(User)
                .filter(User.email == clean_email, User.id != student.user_id)
                .first()
            )
            if duplicate:
                raise ValueError("Email is already assigned to another user.")
            student.user.email = clean_email

        if payload.full_name is not None:
            student.user.full_name = payload.full_name.strip()
        if payload.is_active is not None:
            student.user.is_active = payload.is_active
        if payload.department is not None:
            student.department = payload.department.strip()
        if payload.batch_year is not None:
            student.batch_year = payload.batch_year
        if payload.current_semester is not None:
            student.current_semester = payload.current_semester
        if payload.phone is not None:
            student.phone = payload.phone.strip() if payload.phone else None

        db.commit()
        db.refresh(student)
        return student

    @staticmethod
    def delete_student(db: Session, student_id: int) -> bool:
        """Delete a student and cascade-delete the linked user account."""
        student = StudentService.get_student_by_id(db, student_id)
        if not student:
            return False
        user = student.user
        db.delete(user)
        db.commit()
        return True
