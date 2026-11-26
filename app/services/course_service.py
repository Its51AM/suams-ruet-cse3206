"""Business logic for Courses, Teacher assignment, and Student Enrollments."""

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload
from app.core.security import hash_password
from app.models.course import Course, Enrollment
from app.models.user import Student, Teacher, User, UserRole
from app.schemas.course import CourseCreate, CourseUpdate, TeacherCreate


class CourseService:
    """Service managing university courses, teacher assignments, and enrollments."""

    @staticmethod
    def create_teacher(db: Session, payload: TeacherCreate) -> Teacher:
        """Create a Teacher user account and teacher profile."""
        clean_username = payload.username.strip()
        clean_email = str(payload.email).strip().lower()
        clean_emp = payload.employee_id.strip()

        existing_user = (
            db.query(User)
            .filter(or_(User.username == clean_username, User.email == clean_email))
            .first()
        )
        if existing_user:
            raise ValueError("A user with this username or email already exists.")

        existing_emp = db.query(Teacher).filter(Teacher.employee_id == clean_emp).first()
        if existing_emp:
            raise ValueError("A teacher with this employee ID already exists.")

        user = User(
            username=clean_username,
            email=clean_email,
            full_name=payload.full_name.strip(),
            password_hash=hash_password(payload.password),
            role=UserRole.TEACHER.value,
            is_active=True,
        )
        db.add(user)
        db.flush()

        teacher = Teacher(
            user_id=user.id,
            employee_id=clean_emp,
            department=payload.department.strip(),
            designation=payload.designation.strip(),
        )
        db.add(teacher)
        db.commit()
        db.refresh(teacher)
        return teacher

    @staticmethod
    def list_teachers(db: Session) -> list[Teacher]:
        """List all teachers ordered by employee ID."""
        return (
            db.query(Teacher)
            .options(joinedload(Teacher.user))
            .order_by(Teacher.employee_id.asc())
            .all()
        )

    @staticmethod
    def create_course(db: Session, payload: CourseCreate) -> Course:
        """Create a new course and optionally assign a teacher."""
        clean_code = payload.course_code.strip().upper()
        if db.query(Course).filter(Course.course_code == clean_code).first():
            raise ValueError("A course with this course code already exists.")

        if payload.teacher_id is not None:
            teacher = db.query(Teacher).filter(Teacher.id == payload.teacher_id).first()
            if not teacher:
                raise LookupError("Assigned teacher not found.")

        course = Course(
            course_code=clean_code,
            title=payload.title.strip(),
            credits=payload.credits,
            semester=payload.semester,
            department=payload.department.strip(),
            teacher_id=payload.teacher_id,
        )
        db.add(course)
        db.commit()
        db.refresh(course)
        return course

    @staticmethod
    def list_courses(
        db: Session,
        *,
        semester: int | None = None,
        teacher_id: int | None = None,
        department: str | None = None,
    ) -> list[Course]:
        """List courses with optional filters."""
        query = db.query(Course).options(joinedload(Course.teacher).joinedload(Teacher.user))
        if semester is not None:
            query = query.filter(Course.semester == semester)
        if teacher_id is not None:
            query = query.filter(Course.teacher_id == teacher_id)
        if department:
            query = query.filter(Course.department.ilike(department.strip()))
        return query.order_by(Course.semester.asc(), Course.course_code.asc()).all()

    @staticmethod
    def get_course_by_id(db: Session, course_id: int) -> Course | None:
        """Fetch a single course by ID."""
        return (
            db.query(Course)
            .options(joinedload(Course.teacher).joinedload(Teacher.user))
            .filter(Course.id == course_id)
            .first()
        )

    @staticmethod
    def update_course(db: Session, course_id: int, payload: CourseUpdate) -> Course:
        """Update course metadata or teacher assignment."""
        course = CourseService.get_course_by_id(db, course_id)
        if not course:
            raise LookupError("Course not found.")

        if payload.teacher_id is not None:
            teacher = db.query(Teacher).filter(Teacher.id == payload.teacher_id).first()
            if not teacher:
                raise LookupError("Assigned teacher not found.")
            course.teacher_id = payload.teacher_id

        if payload.title is not None:
            course.title = payload.title.strip()
        if payload.credits is not None:
            course.credits = payload.credits
        if payload.semester is not None:
            course.semester = payload.semester
        if payload.department is not None:
            course.department = payload.department.strip()

        db.commit()
        db.refresh(course)
        return course

    @staticmethod
    def delete_course(db: Session, course_id: int) -> bool:
        """Delete a course."""
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            return False
        db.delete(course)
        db.commit()
        return True

    @staticmethod
    def enroll_student(db: Session, course_id: int, student_id: int) -> Enrollment:
        """Register a student in a course, guarding against duplicates."""
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise LookupError("Course not found.")

        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise LookupError("Student not found.")

        existing = (
            db.query(Enrollment)
            .filter(Enrollment.course_id == course_id, Enrollment.student_id == student_id)
            .first()
        )
        if existing:
            raise ValueError("Student is already enrolled in this course.")

        enrollment = Enrollment(course_id=course_id, student_id=student_id)
        db.add(enrollment)
        db.commit()
        db.refresh(enrollment)
        return enrollment

    @staticmethod
    def list_course_students(db: Session, course_id: int) -> list[Student]:
        """List all students enrolled in a given course."""
        enrollments = (
            db.query(Enrollment)
            .options(joinedload(Enrollment.student).joinedload(Student.user))
            .filter(Enrollment.course_id == course_id)
            .all()
        )
        return [e.student for e in enrollments if e.student is not None]

    @staticmethod
    def list_student_courses(db: Session, student_id: int) -> list[Course]:
        """List all courses a student is registered for."""
        enrollments = (
            db.query(Enrollment)
            .options(
                joinedload(Enrollment.course)
                .joinedload(Course.teacher)
                .joinedload(Teacher.user)
            )
            .filter(Enrollment.student_id == student_id)
            .all()
        )
        return [e.course for e in enrollments if e.course is not None]
