"""Business logic for Notices and User Notifications."""

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload
from app.models.course import Course
from app.models.notice import Notice, Notification
from app.models.user import UserRole
from app.patterns.observer import AcademicEventPublisher
from app.schemas.notice import NoticeCreate


class NoticeService:
    """Service for publishing announcements and managing user notifications."""

    @staticmethod
    def publish_notice(
        db: Session,
        *,
        payload: NoticeCreate,
        author_id: int,
        publisher: AcademicEventPublisher | None = None,
    ) -> Notice:
        """Persist a new notice and notify observers."""
        if payload.course_id is not None:
            course = db.query(Course).filter(Course.id == payload.course_id).first()
            if not course:
                raise LookupError("Referenced course not found.")

        notice = Notice(
            title=payload.title.strip(),
            content=payload.content.strip(),
            target_role=payload.target_role,
            course_id=payload.course_id,
            author_id=author_id,
        )
        db.add(notice)
        db.flush()

        if publisher is not None:
            publisher.notify("notice_published", {"db": db, "notice": notice})

        db.commit()
        db.refresh(notice)
        return notice

    @staticmethod
    def list_notices(db: Session, *, role: str) -> list[Notice]:
        """List notices visible to a specific user role."""
        query = db.query(Notice).options(joinedload(Notice.author), joinedload(Notice.course))
        if role != UserRole.ADMIN.value:
            query = query.filter(or_(Notice.target_role == "all", Notice.target_role == role))
        return query.order_by(Notice.created_at.desc(), Notice.id.desc()).all()

    @staticmethod
    def delete_notice(db: Session, notice_id: int) -> bool:
        """Delete a notice by ID."""
        notice = db.query(Notice).filter(Notice.id == notice_id).first()
        if not notice:
            return False
        db.delete(notice)
        db.commit()
        return True

    @staticmethod
    def list_user_notifications(db: Session, user_id: int) -> list[Notification]:
        """Retrieve notifications addressed to a user, newest first."""
        return (
            db.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
            .all()
        )

    @staticmethod
    def mark_notification_read(db: Session, notification_id: int, user_id: int) -> Notification:
        """Mark a user's notification as read."""
        notif = (
            db.query(Notification)
            .filter(Notification.id == notification_id, Notification.user_id == user_id)
            .first()
        )
        if not notif:
            raise LookupError("Notification not found.")
        notif.is_read = True
        db.commit()
        db.refresh(notif)
        return notif
