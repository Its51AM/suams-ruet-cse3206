"""TDD Unit and API tests for Increment 1: Authentication & Role Management."""

from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.models.user import User, UserRole
from app.services.auth_service import AuthService


pytestmark = pytest.mark.unit


def test_password_hashing_and_verification():
    """Passwords must be securely hashed and never stored in plaintext."""
    raw = "Ruet@2026Secure!"
    hashed = hash_password(raw)

    assert hashed != raw
    assert hashed.startswith("$2")
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_jwt_token_roundtrip():
    """JWT tokens should encode and decode user subject and role accurately."""
    token = create_access_token({"sub": "admin@ruet.ac.bd", "role": UserRole.ADMIN.value})
    payload = decode_access_token(token)

    assert payload["sub"] == "admin@ruet.ac.bd"
    assert payload["role"] == "admin"
    assert "exp" in payload


def test_jwt_token_invalid_raises():
    """Tampered or malformed JWT tokens must be rejected."""
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token("invalid.token.value")
    assert exc_info.value.status_code == 401


def test_auth_service_authenticate_success_with_mock_db():
    """AuthService.authenticate_user verifies credentials using mocked DB query."""
    mock_db = MagicMock()
    user = User(
        id=1,
        username="teacher1",
        email="teacher1@ruet.ac.bd",
        full_name="Dr. Rahman",
        password_hash=hash_password("Pass1234!"),
        role=UserRole.TEACHER.value,
        is_active=True,
    )
    mock_db.query.return_value.filter.return_value.first.return_value = user

    result = AuthService.authenticate_user(mock_db, "teacher1@ruet.ac.bd", "Pass1234!")
    assert result is not None
    assert result.id == 1
    assert result.role == "teacher"


def test_auth_service_rejects_inactive_user_with_mock_db():
    """Inactive accounts must not be allowed to authenticate."""
    mock_db = MagicMock()
    inactive_user = User(
        id=2,
        username="inactive",
        email="inactive@ruet.ac.bd",
        full_name="Inactive User",
        password_hash=hash_password("Pass1234!"),
        role=UserRole.STUDENT.value,
        is_active=False,
    )
    mock_db.query.return_value.filter.return_value.first.return_value = inactive_user

    result = AuthService.authenticate_user(mock_db, "inactive@ruet.ac.bd", "Pass1234!")
    assert result is None


def test_api_login_logout_and_rbac(client, db_session):
    """End-to-end API flow: login sets cookie, RBAC enforces role, logout clears cookie."""
    admin = AuthService.create_user(
        db_session,
        username="sysadmin",
        email="admin@ruet.ac.bd",
        full_name="System Admin",
        password="AdminPassword!1",
        role=UserRole.ADMIN,
    )
    student = AuthService.create_user(
        db_session,
        username="std2103001",
        email="2103001@student.ruet.ac.bd",
        full_name="Ayesha Siddika",
        password="StudentPassword!1",
        role=UserRole.STUDENT,
    )
    assert admin.id != student.id

    # Invalid login
    bad_resp = client.post(
        "/api/auth/login",
        json={"identifier": "admin@ruet.ac.bd", "password": "wrong"},
    )
    assert bad_resp.status_code == 401

    # Login as student
    login_resp = client.post(
        "/api/auth/login",
        json={"identifier": "2103001@student.ruet.ac.bd", "password": "StudentPassword!1"},
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["role"] == "student"

    # Student can access /api/auth/me
    me_resp = client.get("/api/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "std2103001"

    # Student cannot access admin-only endpoint
    forbidden_resp = client.get("/api/auth/admin-check")
    assert forbidden_resp.status_code == 403

    # Logout clears session
    logout_resp = client.post("/api/auth/logout")
    assert logout_resp.status_code == 200
    after_logout = client.get("/api/auth/me")
    assert after_logout.status_code == 401

    # Admin login succeeds on admin-only endpoint
    admin_login = client.post(
        "/api/auth/login",
        json={"identifier": "sysadmin", "password": "AdminPassword!1"},
    )
    assert admin_login.status_code == 200
    admin_check = client.get("/api/auth/admin-check")
    assert admin_check.status_code == 200
    assert admin_check.json()["status"] == "ok"
