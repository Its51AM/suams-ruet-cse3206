"""Business logic for Result Publishing and Grade Calculation."""

from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload
from app.models.course import Course, Enrollment
from app.models.result import Result
from app.models.user import Student
from app.patterns.observer import AcademicEventPublisher


class GradeCalculator:
    """RUET-aligned Bangladesh UGC 4.00 grading scale calculator."""

    SCALE: tuple[tuple[float, str, float], ...] = (
        (80.0, "A+", 4.00),
        (75.0, "A", 3.75),
        (70.0, "A-", 3.50),
        (65.0, "B+", 3.25),
        (60.0, "B", 3.00),
        (55.0, "B-", 2.75),
        (50.0, "C+", 2.50),
        (45.0, "C", 2.25),
        (40.0, "D", 2.00),
        (0.0, "F", 0.00),
    )

    @classmethod
    def calculate_grade(cls, marks: float) -> tuple[str, float]:
        """Return (letter_grade, grade_point) for marks in [0, 100]."""
        if marks < 0.0 or marks > 100.0:
            raise ValueError("Marks must be between 0 and 100.")
        for threshold, letter, gp in cls.SCALE:
            if marks >= threshold:
                return letter, gp
        return "F", 0.00

    @staticmethod
    def calculate_gpa(results: list[Result]) -> tuple[float, float]:
        """Return (total_credits, weighted_gpa) rounded to 2 decimal places."""
        if not results:
            return 0.0, 0.0
        total_credits = sum(r.course.credits for r in results if r.course is not None)
        if total_credits <= 0:
            return 0.0, 0.0
        weighted_points = sum(
            r.grade_point * r.course.credits for r in results if r.course is not None
        )
        return round(total_credits, 2), round(weighted_points / total_credits, 2)


class ResultService:
    """Service for publishing results and generating student transcripts."""

    @staticmethod
    def publish_result(
        db: Session,
        *,
        student_id: int,
        course_id: int,
        marks: float,
        publisher: AcademicEventPublisher | None = None,
    ) -> Result:
        """Validate enrollment, calculate grade, persist result, and notify observers."""
        student = (
            db.query(Student)
            .options(joinedload(Student.user))
            .filter(Student.id == student_id)
            .first()
        )
        if not student:
            raise LookupError("Student not found.")

        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise LookupError("Course not found.")

        enrolled = (
            db.query(Enrollment)
            .filter(Enrollment.student_id == student_id, Enrollment.course_id == course_id)
            .first()
        )
        if not enrolled:
            raise ValueError("Student must be enrolled in the course before publishing results.")

        letter_grade, grade_point = GradeCalculator.calculate_grade(marks)
        existing = (
            db.query(Result)
            .filter(Result.student_id == student_id, Result.course_id == course_id)
            .first()
        )
        if existing:
            existing.marks = marks
            existing.letter_grade = letter_grade
            existing.grade_point = grade_point
            existing.published_at = datetime.now(timezone.utc)
            result = existing
        else:
            result = Result(
                student_id=student_id,
                course_id=course_id,
                marks=marks,
                letter_grade=letter_grade,
                grade_point=grade_point,
            )
            db.add(result)

        db.flush()

        if publisher is not None:
            publisher.notify(
                "result_published",
                {
                    "db": db,
                    "student": student,
                    "course": course,
                    "marks": marks,
                    "letter_grade": letter_grade,
                    "grade_point": grade_point,
                },
            )

        db.commit()
        db.refresh(result)
        return result

    @staticmethod
    def get_student_transcript(db: Session, student_id: int) -> dict:
        """Fetch all published results and computed GPA for a student."""
        results = (
            db.query(Result)
            .options(joinedload(Result.course), joinedload(Result.student).joinedload(Student.user))
            .filter(Result.student_id == student_id)
            .order_by(Result.course_id.asc())
            .all()
        )
        total_credits, gpa = GradeCalculator.calculate_gpa(results)
        return {
            "student_id": student_id,
            "total_credits": total_credits,
            "gpa": gpa,
            "results": results,
        }

    @staticmethod
    def get_course_results(db: Session, course_id: int) -> list[Result]:
        """Fetch all published results for a course."""
        return (
            db.query(Result)
            .options(joinedload(Result.course), joinedload(Result.student).joinedload(Student.user))
            .filter(Result.course_id == course_id)
            .order_by(Result.student_id.asc())
            .all()
        )
