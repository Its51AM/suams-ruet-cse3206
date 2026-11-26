"""Factory Pattern: Centralizes creation of notification provider adapters."""

from sqlalchemy.orm import Session
from app.patterns.adapters import (
    EmailNotificationAdapter,
    ExternalEmailClient,
    INotificationService,
    InAppNotificationAdapter,
)


class NotificationFactory:
    """Creational factory returning INotificationService instances by channel name."""

    @staticmethod
    def create_provider(
        channel: str,
        *,
        db: Session,
        email_client: ExternalEmailClient | None = None,
    ) -> INotificationService:
        """Instantiate the requested notification adapter or raise ValueError."""
        normalized = channel.strip().lower()
        if normalized == "in_app":
            return InAppNotificationAdapter(db=db)
        if normalized == "email":
            return EmailNotificationAdapter(db=db, email_client=email_client)
        raise ValueError(f"Unsupported notification channel: '{channel}'")
