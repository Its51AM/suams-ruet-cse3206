"""Notices and Notifications API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.notice import Notice
from app.models.user import User, UserRole
from app.patterns.observer import build_default_publisher
from app.schemas.notice import NoticeCreate, NoticeResponse, NotificationResponse
from app.services.notice_service import NoticeService

router = APIRouter(prefix="/api/notices", tags=["Notices & Notifications"])


def _notice_to_response(notice: Notice) -> NoticeResponse:
    return NoticeResponse(
        id=notice.id,
        title=notice.title,
        content=notice.content,
        target_role=notice.target_role,
        course_id=notice.course_id,
        course_code=notice.course.course_code if notice.course else None,
        author_name=notice.author.full_name if notice.author else "Administration",
        created_at=notice.created_at,
    )


@router.post("", response_model=NoticeResponse, status_code=status.HTTP_201_CREATED)
def publish_notice(
    payload: NoticeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.TEACHER)),
):
    """Publish a notice and notify subscribers via the Observer pattern."""
    try:
        publisher = build_default_publisher()
        notice = NoticeService.publish_notice(
            db, payload=payload, author_id=current_user.id, publisher=publisher
        )
        return _notice_to_response(notice)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("", response_model=list[NoticeResponse])
def list_notices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List announcements visible to the authenticated user's role."""
    notices = NoticeService.list_notices(db, role=current_user.role)
    return [_notice_to_response(n) for n in notices]


@router.delete("/{notice_id}")
def delete_notice(
    notice_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Delete a notice (Admin only)."""
    if not NoticeService.delete_notice(db, notice_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found.")
    return {"message": "Notice deleted successfully."}


@router.get("/notifications/my", response_model=list[NotificationResponse])
def list_my_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List personal notifications generated for the authenticated user."""
    return NoticeService.list_user_notifications(db, current_user.id)


@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a personal notification as read."""
    try:
        return NoticeService.mark_notification_read(db, notification_id, current_user.id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
