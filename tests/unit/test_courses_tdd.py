"""TDD Unit and API tests for Increment 3: Course & Enrollment Management."""

from unittest.mock import MagicMock
import pytest
from app.models.course import Course
from app.models.user import Teacher, UserRole
from app.services.auth_service import AuthService
from app.services.course_service import CourseService


pytestmark = pytest.mark.unit


def _login_as(client, identifier: str, password: str) -> None:
    resp = client.post("/api/auth/login", json={"identifier": identifier, "password": password})
    assert resp.status_code == 200


def test_course_service_duplicate_enrollment_guard_with_mock_db():
    """CourseService.enroll_student raises ValueError if student is already enrolled."""
    mock_db = MagicMock()
    # Course exists, Student exists, Existing enrollment found
    mock_course = Course(id=1, course_code="CSE 3206", title="SWE Sessional", credits=1.5, semester=6, department="CSE")
    mock_db.query.return_value.filter.return_value.first.side_effect = [
        mock_course,
        MagicMock(id=2),
        MagicMock(id=99),
    ]

    with pytest.raises(ValueError, match="already enrolled"):
        CourseService.enroll_student(mock_db, course_id=1, student_id=2)


def test_course_management_and_enrollment_flow(client, db_session):
    """Admin creates courses & assigns teachers; students register in courses."""
    AuthService.create_user(
        db_session,
        username="admin",
        email="admin@ruet.ac.bd",
        full_name="Admin",
        password="AdminPass!1",
        role=UserRole.ADMIN,
    )
    teacher_user = AuthService.create_user(
        db_session,
        username="dr_karim",
        email="karim@ruet.ac.bd",
        full_name="Dr. Karim",
        password="TeacherPass!1",
        role=UserRole.TEACHER,
    )
    teacher = Teacher(
        user_id=teacher_user.id,
        employee_id="RUET-CSE-101",
        department="CSE",
        designation="Associate Professor",
    )
    db_session.add(teacher)
    db_session.commit()
    db_session.refresh(teacher)

    _login_as(client, "admin", "AdminPass!1")

    # Create student via API
    s_resp = client.post(
        "/api/students",
        json={
            "username": "std2103005",
            "email": "2103005@student.ruet.ac.bd",
            "full_name": "Farhan Labib",
            "password": "StudentPass!1",
            "roll_number": "2103005",
            "department": "CSE",
            "batch_year": 2021,
            "current_semester": 6,
        },
    )
    assert s_resp.status_code == 201
    student_id = s_resp.json()["id"]

    # Create course
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
    assert c_resp.status_code == 201
    course = c_resp.json()
    assert course["teacher_id"] == teacher.id

    # Student self-registers for the course
    _login_as(client, "std2103005", "StudentPass!1")
    enroll_resp = client.post(f"/api/courses/{course['id']}/enroll", json={})
    assert enroll_resp.status_code == 201

    # Duplicate enrollment rejected
    dup_enroll = client.post(f"/api/courses/{course['id']}/enroll", json={})
    assert dup_enroll.status_code == 400

    # Student views registered courses
    my_courses = client.get("/api/courses/my")
    assert my_courses.status_code == 200
    assert len(my_courses.json()) == 1
    assert my_courses.json()[0]["course_code"] == "CSE 3206"

    # Teacher views assigned courses and enrolled students
    _login_as(client, "dr_karim", "TeacherPass!1")
    teacher_courses = client.get("/api/courses/my")
    assert teacher_courses.status_code == 200
    assert len(teacher_courses.json()) == 1

    roster = client.get(f"/api/courses/{course['id']}/students")
    assert roster.status_code == 200
    assert len(roster.json()) == 1
    assert roster.json()[0]["id"] == student_id
