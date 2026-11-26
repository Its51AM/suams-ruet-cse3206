"""TDD Unit and API tests for Increment 4: Attendance Management."""

from datetime import date
from unittest.mock import MagicMock
import pytest
from app.models.course import Course
from app.models.user import Teacher, UserRole
from app.services.attendance_service import AttendanceService
from app.services.auth_service import AuthService


pytestmark = pytest.mark.unit


def _login_as(client, identifier: str, password: str) -> None:
    resp = client.post("/api/auth/login", json={"identifier": identifier, "password": password})
    assert resp.status_code == 200


def test_attendance_percentage_calculation_with_mock_db():
    """AttendanceService computes summary statistics accurately from mocked records."""
    mock_db = MagicMock()
    records = [
        MagicMock(status="Present"),
        MagicMock(status="Present"),
        MagicMock(status="Late"),
        MagicMock(status="Absent"),
    ]
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = records

    summary = AttendanceService.get_student_attendance_summary(mock_db, student_id=1)
    assert summary["total_classes"] == 4
    assert summary["present_count"] == 2
    assert summary["late_count"] == 1
    assert summary["absent_count"] == 1
    assert summary["attendance_percentage"] == 75.0


def test_attendance_recording_upsert_and_student_view(client, db_session):
    """Assigned teacher records/updates attendance; student views attendance summary."""
    AuthService.create_user(
        db_session,
        username="admin",
        email="admin@ruet.ac.bd",
        full_name="Admin",
        password="AdminPass!1",
        role=UserRole.ADMIN,
    )
    t1_user = AuthService.create_user(
        db_session,
        username="teacher1",
        email="t1@ruet.ac.bd",
        full_name="Teacher One",
        password="TeacherPass!1",
        role=UserRole.TEACHER,
    )
    t2_user = AuthService.create_user(
        db_session,
        username="teacher2",
        email="t2@ruet.ac.bd",
        full_name="Teacher Two",
        password="TeacherPass!1",
        role=UserRole.TEACHER,
    )
    t1 = Teacher(user_id=t1_user.id, employee_id="EMP-1", department="CSE", designation="Lecturer")
    t2 = Teacher(user_id=t2_user.id, employee_id="EMP-2", department="CSE", designation="Lecturer")
    db_session.add_all([t1, t2])
    db_session.commit()
    db_session.refresh(t1)
    db_session.refresh(t2)

    _login_as(client, "admin", "AdminPass!1")
    s_resp = client.post(
        "/api/students",
        json={
            "username": "std2103011",
            "email": "2103011@student.ruet.ac.bd",
            "full_name": "Mahmudul Hasan",
            "password": "StudentPass!1",
            "roll_number": "2103011",
            "department": "CSE",
            "batch_year": 2021,
            "current_semester": 6,
        },
    )
    student_id = s_resp.json()["id"]

    c_resp = client.post(
        "/api/courses",
        json={
            "course_code": "CSE 3201",
            "title": "Software Engineering",
            "credits": 3.0,
            "semester": 6,
            "department": "CSE",
            "teacher_id": t1.id,
        },
    )
    course_id = c_resp.json()["id"]
    assert client.post(f"/api/courses/{course_id}/enroll", json={"student_id": student_id}).status_code == 201

    # Unassigned teacher cannot record attendance
    _login_as(client, "teacher2", "TeacherPass!1")
    forbidden = client.post(
        f"/api/attendance/courses/{course_id}",
        json={
            "attendance_date": date(2026, 11, 20).isoformat(),
            "entries": [{"student_id": student_id, "status": "Present"}],
        },
    )
    assert forbidden.status_code == 403

    # Assigned teacher marks Absent, then updates same date to Present (upsert, no duplicate)
    _login_as(client, "teacher1", "TeacherPass!1")
    mark1 = client.post(
        f"/api/attendance/courses/{course_id}",
        json={
            "attendance_date": date(2026, 11, 20).isoformat(),
            "entries": [{"student_id": student_id, "status": "Absent"}],
        },
    )
    assert mark1.status_code == 200

    mark2 = client.post(
        f"/api/attendance/courses/{course_id}",
        json={
            "attendance_date": date(2026, 11, 20).isoformat(),
            "entries": [{"student_id": student_id, "status": "Present"}],
        },
    )
    assert mark2.status_code == 200

    mark3 = client.post(
        f"/api/attendance/courses/{course_id}",
        json={
            "attendance_date": date(2026, 11, 21).isoformat(),
            "entries": [{"student_id": student_id, "status": "Absent"}],
        },
    )
    assert mark3.status_code == 200

    # Student views own attendance summary: 1 Present, 1 Absent => 50.0%
    _login_as(client, "std2103011", "StudentPass!1")
    my_att = client.get(f"/api/attendance/my?course_id={course_id}")
    assert my_att.status_code == 200
    data = my_att.json()
    assert data["total_classes"] == 2
    assert data["present_count"] == 1
    assert data["absent_count"] == 1
    assert data["attendance_percentage"] == 50.0
