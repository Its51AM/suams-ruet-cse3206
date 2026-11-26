"""Observer Pattern: Broadcasts academic events to student notification observers."""

from abc import ABC, abstractmethod
from sqlalchemy.orm import Session, joinedload
from app.models.course import Enrollment
from app.models.user import Student, User, UserRole
from app.patterns.factory import NotificationFactory


class AcademicEventObserver(ABC):
    """Observer interface reacting to academic domain events."""

    @abstractmethod
    def update(self, event_type: str, payload: dict) -> None:
        """Handle an academic event notification."""


class AcademicEventPublisher:
    """Subject maintaining subscribers and notifying them of academic events."""

    def __init__(self) -> None:
        self._observers: list[AcademicEventObserver] = []

    def attach(self, observer: AcademicEventObserver) -> None:
        """Register an observer if not already attached."""
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: AcademicEventObserver) -> None:
        """Remove an observer from notifications."""
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, event_type: str, payload: dict) -> None:
        """Notify all attached observers about an event."""
        for observer in list(self._observers):
            observer.update(event_type, payload)


class StudentNotificationObserver(AcademicEventObserver):
    """Concrete observer dispatching In-App notifications via NotificationFactory."""

    def __init__(self, channels: tuple[str, ...] = ("in_app",)) -> None:
        self.channels = channels

    def update(self, event_type: str, payload: dict) -> None:
        db: Session | None = payload.get("db")
        if db is None:
            return

        if event_type == "result_published":
            student = payload["student"]
            course = payload["course"]
            subject = f"Result Published: {course.course_code}"
            body = (
                f"Your grade for {course.course_code} ({course.title}) has been published: "
                f"{payload['marks']} marks ({payload['letter_grade']}, GP {payload['grade_point']:.2f})."
            )
            self._dispatch_to_users(db, [student.user], subject, body)

        elif event_type == "notice_published":
            notice = payload["notice"]
            recipients = self._resolve_notice_recipients(db, notice)
            subject = f"New Notice: {notice.title}"
            body = notice.content
            self._dispatch_to_users(db, recipients, subject, body)

    def _dispatch_to_users(self, db: Session, users: list[User], subject: str, body: str) -> None:
        for channel in self.channels:
            provider = NotificationFactory.create_provider(channel, db=db)
            for user in users:
                if user and user.is_active:
                    provider.send(user, subject, body)

    @staticmethod
    def _resolve_notice_recipients(db: Session, notice) -> list[User]:
        if notice.course_id is not None:
            enrollments = (
                db.query(Enrollment)
                .options(joinedload(Enrollment.student).joinedload(Student.user))
                .filter(Enrollment.course_id == notice.course_id)
                .all()
            )
            return [e.student.user for e in enrollments if e.student and e.student.user]

        query = db.query(User).filter(User.is_active.is_(True))
        if notice.target_role in (UserRole.STUDENT.value, UserRole.TEACHER.value):
            query = query.filter(User.role == notice.target_role)
        else:
            query = query.filter(User.role.in_([UserRole.STUDENT.value, UserRole.TEACHER.value]))
        return query.all()


def build_default_publisher() -> AcademicEventPublisher:
    """Create a configured publisher with the student notification observer attached."""
    publisher = AcademicEventPublisher()
    publisher.attach(StudentNotificationObserver(channels=("in_app",)))
    return publisher
