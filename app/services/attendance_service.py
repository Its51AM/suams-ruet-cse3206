"""Business logic for Attendance Management."""

from datetime import date, datetime, timezone
from sqlalchemy.orm import Session, joinedload
from app.models.attendance import AttendanceRecord, AttendanceStatus
from app.models.course import Course, Enrollment
from app.models.user import Student
from app.schemas.attendance import AttendanceEntry


class AttendanceService:
    """Service for recording and summarizing course attendance."""

    @staticmethod
    def record_attendance(
        db: Session,
        *,
        course_id: int,
        attendance_date: date,
        entries: list[AttendanceEntry],
        marked_by_user_id: int,
    ) -> list[AttendanceRecord]:
        """Create or update attendance records for enrolled students on a date."""
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise LookupError("Course not found.")

        enrolled_ids = {
            row.student_id
            for row in db.query(Enrollment).filter(Enrollment.course_id == course_id).all()
        }

        saved_records: list[AttendanceRecord] = []
        for entry in entries:
            if entry.student_id not in enrolled_ids:
                raise ValueError(f"Student {entry.student_id} is not enrolled in this course.")

            existing = (
                db.query(AttendanceRecord)
                .filter(
                    AttendanceRecord.course_id == course_id,
                    AttendanceRecord.student_id == entry.student_id,
                    AttendanceRecord.attendance_date == attendance_date,
                )
                .first()
            )
            status_val = entry.status.value if isinstance(entry.status, AttendanceStatus) else str(entry.status)
            if existing:
                existing.status = status_val
                existing.marked_by = marked_by_user_id
                existing.updated_at = datetime.now(timezone.utc)
                saved_records.append(existing)
            else:
                record = AttendanceRecord(
                    student_id=entry.student_id,
                    course_id=course_id,
                    attendance_date=attendance_date,
                    status=status_val,
                    marked_by=marked_by_user_id,
                )
                db.add(record)
                saved_records.append(record)

        db.commit()
        for rec in saved_records:
            db.refresh(rec)
        return saved_records

    @staticmethod
    def get_course_attendance(
        db: Session,
        course_id: int,
        attendance_date: date | None = None,
    ) -> list[AttendanceRecord]:
        """Retrieve attendance records for a course, optionally filtered by date."""
        query = (
            db.query(AttendanceRecord)
            .options(
                joinedload(AttendanceRecord.student).joinedload(Student.user),
                joinedload(AttendanceRecord.course),
            )
            .filter(AttendanceRecord.course_id == course_id)
        )
        if attendance_date is not None:
            query = query.filter(AttendanceRecord.attendance_date == attendance_date)
        return query.order_by(AttendanceRecord.attendance_date.desc(), AttendanceRecord.student_id.asc()).all()

    @staticmethod
    def get_student_attendance_summary(
        db: Session,
        student_id: int,
        course_id: int | None = None,
    ) -> dict:
        """Compute attendance counts and percentage (Present + Late count as attended)."""
        query = db.query(AttendanceRecord).filter(AttendanceRecord.student_id == student_id)
        if course_id is not None:
            query = query.filter(AttendanceRecord.course_id == course_id)

        records = query.order_by(AttendanceRecord.attendance_date.desc()).all()
        total = len(records)
        present_count = sum(1 for r in records if r.status == AttendanceStatus.PRESENT.value)
        late_count = sum(1 for r in records if r.status == AttendanceStatus.LATE.value)
        absent_count = sum(1 for r in records if r.status == AttendanceStatus.ABSENT.value)

        percentage = round(((present_count + late_count) / total) * 100.0, 2) if total > 0 else 0.0
        return {
            "student_id": student_id,
            "total_classes": total,
            "present_count": present_count,
            "late_count": late_count,
            "absent_count": absent_count,
            "attendance_percentage": percentage,
            "records": records,
        }
