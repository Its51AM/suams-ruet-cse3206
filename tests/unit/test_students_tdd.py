"""TDD Unit and API tests for Increment 2: Student Management."""

from unittest.mock import MagicMock
import pytest
from app.models.user import Student, User, UserRole
from app.schemas.student import StudentCreate, StudentUpdate
from app.services.auth_service import AuthService
from app.services.student_service import StudentService


pytestmark = pytest.mark.unit


def _login_as(client, identifier: str, password: str) -> None:
    resp = client.post("/api/auth/login", json={"identifier": identifier, "password": password})
    assert resp.status_code == 200


def test_student_service_get_by_id_with_mock_db():
    """StudentService.get_student_by_id queries SQLAlchemy via mocked session."""
    mock_db = MagicMock()
    expected = Student(
        id=10,
        user_id=5,
        roll_number="2103010",
        department="CSE",
        batch_year=2021,
        current_semester=6,
    )
    mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = expected

    result = StudentService.get_student_by_id(mock_db, 10)
    assert result is expected
    assert result.roll_number == "2103010"


def test_student_crud_and_role_permissions(client, db_session):
    """Admin can CRUD students; students can view own profile but not others or mutate."""
    AuthService.create_user(
        db_session,
        username="admin",
        email="admin@ruet.ac.bd",
        full_name="Admin User",
        password="AdminPass!1",
        role=UserRole.ADMIN,
    )
    AuthService.create_user(
        db_session,
        username="teacher",
        email="teacher@ruet.ac.bd",
        full_name="Teacher User",
        password="TeacherPass!1",
        role=UserRole.TEACHER,
    )

    _login_as(client, "admin", "AdminPass!1")

    # Create two students
    create_resp = client.post(
        "/api/students",
        json={
            "username": "std2103001",
            "email": "2103001@student.ruet.ac.bd",
            "full_name": "Nafis Rahman",
            "password": "StudentPass!1",
            "roll_number": "2103001",
            "department": "CSE",
            "batch_year": 2021,
            "current_semester": 6,
            "phone": "+8801700000001",
        },
    )
    assert create_resp.status_code == 201
    s1 = create_resp.json()
    assert s1["roll_number"] == "2103001"
    assert s1["full_name"] == "Nafis Rahman"

    create_resp2 = client.post(
        "/api/students",
        json={
            "username": "std2103002",
            "email": "2103002@student.ruet.ac.bd",
            "full_name": "Tasnim Akter",
            "password": "StudentPass!1",
            "roll_number": "2103002",
            "department": "EEE",
            "batch_year": 2021,
            "current_semester": 6,
        },
    )
    assert create_resp2.status_code == 201
    s2 = create_resp2.json()

    # Duplicate roll_number must fail with 400
    dup_resp = client.post(
        "/api/students",
        json={
            "username": "std_dup",
            "email": "dup@student.ruet.ac.bd",
            "full_name": "Duplicate",
            "password": "StudentPass!1",
            "roll_number": "2103001",
            "department": "CSE",
            "batch_year": 2021,
            "current_semester": 6,
        },
    )
    assert dup_resp.status_code == 400

    # List & filter by department
    list_resp = client.get("/api/students?department=CSE")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1
    assert list_resp.json()[0]["roll_number"] == "2103001"

    # Update student
    upd_resp = client.put(
        f"/api/students/{s1['id']}",
        json={"current_semester": 7, "full_name": "Nafis Rahman Updated"},
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["current_semester"] == 7
    assert upd_resp.json()["full_name"] == "Nafis Rahman Updated"

    # Student 1 can view own profile, but cannot view Student 2 or delete
    _login_as(client, "std2103001", "StudentPass!1")
    assert client.get("/api/students/me").status_code == 200
    assert client.get(f"/api/students/{s1['id']}").status_code == 200
    assert client.get(f"/api/students/{s2['id']}").status_code == 403
    assert client.delete(f"/api/students/{s1['id']}").status_code == 403

    # Admin deletes student 2
    _login_as(client, "admin", "AdminPass!1")
    del_resp = client.delete(f"/api/students/{s2['id']}")
    assert del_resp.status_code == 200
    assert client.get(f"/api/students/{s2['id']}").status_code == 404
