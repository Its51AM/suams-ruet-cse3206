"""Adapter Pattern: Unifies In-App and External Email notification providers."""

from abc import ABC, abstractmethod
import logging
from sqlalchemy.orm import Session
from app.models.notice import Notification
from app.models.user import User

logger = logging.getLogger(__name__)


class INotificationService(ABC):
    """Target interface expected by SUAMS notification consumers."""

    @abstractmethod
    def send(self, recipient: User, subject: str, body: str) -> bool:
        """Send a notification to a recipient user."""


class ExternalEmailClient:
    """Adaptee simulating an external email gateway with an incompatible API."""

    def __init__(self, sender: str = "noreply@suams.ruet.ac.bd") -> None:
        self.sender = sender

    def dispatch_email(self, *, to_address: str, title: str, text_body: str) -> dict:
        """Third-party style email dispatch method with non-standard signature."""
        logger.info("Simulated SMTP dispatch from %s to %s: %s", self.sender, to_address, title)
        return {"accepted": True, "recipient": to_address, "title": title, "length": len(text_body)}


class InAppNotificationAdapter(INotificationService):
    """Adapter storing notifications in the SUAMS SQLite database."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def send(self, recipient: User, subject: str, body: str) -> bool:
        notification = Notification(
            user_id=recipient.id,
            channel="in_app",
            subject=subject,
            message=body,
            is_read=False,
        )
        self.db.add(notification)
        self.db.flush()
        return True


class EmailNotificationAdapter(INotificationService):
    """Adapter translating INotificationService calls to ExternalEmailClient."""

    def __init__(self, db: Session, email_client: ExternalEmailClient | None = None) -> None:
        self.db = db
        self.email_client = email_client or ExternalEmailClient()

    def send(self, recipient: User, subject: str, body: str) -> bool:
        response = self.email_client.dispatch_email(
            to_address=recipient.email,
            title=subject,
            text_body=body,
        )
        accepted = bool(response.get("accepted", False))
        if accepted:
            self.db.add(
                Notification(
                    user_id=recipient.id,
                    channel="email",
                    subject=subject,
                    message=body,
                    is_read=False,
                )
            )
            self.db.flush()
        return accepted
