"""TDD Unit & Mock tests for Increment 6: Notices and Design Patterns (Factory, Adapter, Observer)."""

from unittest.mock import MagicMock
import pytest
from app.models.user import Teacher, User, UserRole
from app.patterns.adapters import (
    EmailNotificationAdapter,
    ExternalEmailClient,
    INotificationService,
    InAppNotificationAdapter,
)
from app.patterns.factory import NotificationFactory
from app.patterns.observer import (
    AcademicEventObserver,
    AcademicEventPublisher,
    StudentNotificationObserver,
)
from app.services.auth_service import AuthService


pytestmark = pytest.mark.unit


def _login_as(client, identifier: str, password: str) -> None:
    resp = client.post("/api/auth/login", json={"identifier": identifier, "password": password})
    assert resp.status_code == 200


def test_notification_factory_creates_expected_adapters():
    """Factory returns INotificationService implementations and rejects unknown channels."""
    mock_db = MagicMock()
    in_app = NotificationFactory.create_provider("in_app", db=mock_db)
    email = NotificationFactory.create_provider("email", db=mock_db)

    assert isinstance(in_app, INotificationService)
    assert isinstance(in_app, InAppNotificationAdapter)
    assert isinstance(email, INotificationService)
    assert isinstance(email, EmailNotificationAdapter)

    with pytest.raises(ValueError, match="Unsupported notification channel"):
        NotificationFactory.create_provider("carrier_pigeon", db=mock_db)


def test_email_adapter_delegates_to_external_client_via_mock():
    """Adapter translates INotificationService.send() into ExternalEmailClient.dispatch_email()."""
    mock_db = MagicMock()
    mock_client = MagicMock(spec=ExternalEmailClient)
    mock_client.dispatch_email.return_value = {"accepted": True, "message_id": "msg-123"}

    adapter = EmailNotificationAdapter(db=mock_db, email_client=mock_client)
    recipient = User(
        id=42,
        username="std1",
        email="std1@student.ruet.ac.bd",
        full_name="Student One",
        password_hash="hash",
        role=UserRole.STUDENT.value,
    )

    sent = adapter.send(recipient, "Result Published", "Your CSE 3206 result is A+.")
    assert sent is True
    mock_client.dispatch_email.assert_called_once_with(
        to_address="std1@student.ruet.ac.bd",
        title="Result Published",
        text_body="Your CSE 3206 result is A+.",
    )
    mock_db.add.assert_called_once()


def test_observer_publisher_notifies_all_attached_observers():
    """AcademicEventPublisher notifies attached observers and supports detaching."""
    publisher = AcademicEventPublisher()
    obs1 = MagicMock(spec=AcademicEventObserver)
    obs2 = MagicMock(spec=AcademicEventObserver)

    publisher.attach(obs1)
    publisher.attach(obs2)
    publisher.notify("notice_published", {"title": "Midterm Schedule"})

    obs1.update.assert_called_once_with("notice_published", {"title": "Midterm Schedule"})
    obs2.update.assert_called_once_with("notice_published", {"title": "Midterm Schedule"})

    publisher.detach(obs2)
    publisher.notify("result_published", {"course_code": "CSE 3206"})
    assert obs1.update.call_count == 2
    assert obs2.update.call_count == 1


def test_publishing_notice_and_result_triggers_student_notifications(client, db_session):
    """Publishing a notice or result persists In-App notifications for target students."""
    AuthService.create_user(
        db_session,
        username="admin",
        email="admin@ruet.ac.bd",
        full_name="Admin",
        password="AdminPass!1",
        role=UserRole.ADMIN,
    )
    t_user = AuthService.create_user(
        db_session,
        username="teacher_n",
        email="tn@ruet.ac.bd",
        full_name="Dr. Nasir",
        password="TeacherPass!1",
        role=UserRole.TEACHER,
    )
    teacher = Teacher(user_id=t_user.id, employee_id="EMP-77", department="CSE", designation="Professor")
    db_session.add(teacher)
    db_session.commit()
    db_session.refresh(teacher)

    _login_as(client, "admin", "AdminPass!1")
    s_resp = client.post(
        "/api/students",
        json={
            "username": "std2103030",
            "email": "2103030@student.ruet.ac.bd",
            "full_name": "Sadia Afrin",
            "password": "StudentPass!1",
            "roll_number": "2103030",
            "department": "CSE",
            "batch_year": 2021,
            "current_semester": 6,
        },
    )
    student_id = s_resp.json()["id"]

    c_resp = client.post(
        "/api/courses",
        json={
            "course_code": "CSE 3206",
            "title": "Software Engineering Sessional",
            "credits": 1.5,
            "semester": 6,
            "department": "CSE",
            "teacher_id": teacher.id,
        },
    )
    course_id = c_resp.json()["id"]
    assert client.post(f"/api/courses/{course_id}/enroll", json={"student_id": student_id}).status_code == 201

    # Admin publishes general student notice
    n_resp = client.post(
        "/api/notices",
        json={
            "title": "Class Test Rescheduled",
            "content": "CSE 3206 viva will be held on Sunday at 10 AM.",
            "target_role": "student",
        },
    )
    assert n_resp.status_code == 201

    # Teacher publishes result -> also generates student notification via Observer
    _login_as(client, "teacher_n", "TeacherPass!1")
    r_resp = client.post(
        "/api/results",
        json={"student_id": student_id, "course_id": course_id, "marks": 88.0},
    )
    assert r_resp.status_code == 200

    # Student sees notices and both notifications
    _login_as(client, "std2103030", "StudentPass!1")
    notices = client.get("/api/notices")
    assert notices.status_code == 200
    assert len(notices.json()) == 1

    notifs = client.get("/api/notices/notifications/my")
    assert notifs.status_code == 200
    subjects = [item["subject"] for item in notifs.json()]
    assert any("Class Test Rescheduled" in s for s in subjects)
    assert any("CSE 3206" in s for s in subjects)
