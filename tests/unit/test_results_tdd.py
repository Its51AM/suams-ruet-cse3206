"""TDD Unit and API tests for Increment 5: Result and Grade Management."""

import pytest
from app.models.user import Teacher, UserRole
from app.services.auth_service import AuthService
from app.services.result_service import GradeCalculator


pytestmark = pytest.mark.unit


def _login_as(client, identifier: str, password: str) -> None:
    resp = client.post("/api/auth/login", json={"identifier": identifier, "password": password})
    assert resp.status_code == 200


@pytest.mark.parametrize(
    "marks,expected_letter,expected_gp",
    [
        (85.0, "A+", 4.00),
        (76.0, "A", 3.75),
        (71.0, "A-", 3.50),
        (66.0, "B+", 3.25),
        (60.0, "B", 3.00),
        (56.0, "B-", 2.75),
        (51.0, "C+", 2.50),
        (46.0, "C", 2.25),
        (40.0, "D", 2.00),
        (32.0, "F", 0.00),
    ],
)
def test_grade_calculator_ruet_scale(marks, expected_letter, expected_gp):
    """Verify letter grades and grade points follow the university grading scale."""
    letter, gp = GradeCalculator.calculate_grade(marks)
    assert letter == expected_letter
    assert gp == expected_gp


def test_grade_calculator_rejects_out_of_range():
    """Marks outside [0, 100] must raise ValueError."""
    with pytest.raises(ValueError):
        GradeCalculator.calculate_grade(-5.0)
    with pytest.raises(ValueError):
        GradeCalculator.calculate_grade(105.0)


def test_publish_result_and_gpa_calculation(client, db_session):
    """Teacher publishes marks; grade & GPA are calculated and visible to the student."""
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
        username="prof_ali",
        email="ali@ruet.ac.bd",
        full_name="Prof. Ali",
        password="TeacherPass!1",
        role=UserRole.TEACHER,
    )
    teacher = Teacher(user_id=t_user.id, employee_id="EMP-10", department="CSE", designation="Professor")
    db_session.add(teacher)
    db_session.commit()
    db_session.refresh(teacher)

    _login_as(client, "admin", "AdminPass!1")
    s_resp = client.post(
        "/api/students",
        json={
            "username": "std2103020",
            "email": "2103020@student.ruet.ac.bd",
            "full_name": "Rafiul Islam",
            "password": "StudentPass!1",
            "roll_number": "2103020",
            "department": "CSE",
            "batch_year": 2021,
            "current_semester": 6,
        },
    )
    student_id = s_resp.json()["id"]

    c1 = client.post(
        "/api/courses",
        json={
            "course_code": "CSE 3201",
            "title": "Software Engineering",
            "credits": 3.0,
            "semester": 6,
            "department": "CSE",
            "teacher_id": teacher.id,
        },
    ).json()
    c2 = client.post(
        "/api/courses",
        json={
            "course_code": "CSE 3206",
            "title": "SWE Sessional",
            "credits": 1.5,
            "semester": 6,
            "department": "CSE",
            "teacher_id": teacher.id,
        },
    ).json()

    assert client.post(f"/api/courses/{c1['id']}/enroll", json={"student_id": student_id}).status_code == 201
    assert client.post(f"/api/courses/{c2['id']}/enroll", json={"student_id": student_id}).status_code == 201

    # Teacher publishes 82.0 (A+, 4.00) in 3.0-credit course and 70.0 (A-, 3.50) in 1.5-credit course
    _login_as(client, "prof_ali", "TeacherPass!1")
    r1 = client.post(
        "/api/results",
        json={"student_id": student_id, "course_id": c1["id"], "marks": 82.0},
    )
    assert r1.status_code == 200
    assert r1.json()["letter_grade"] == "A+"
    assert r1.json()["grade_point"] == 4.0

    r2 = client.post(
        "/api/results",
        json={"student_id": student_id, "course_id": c2["id"], "marks": 70.0},
    )
    assert r2.status_code == 200
    assert r2.json()["letter_grade"] == "A-"

    # Student views transcript and weighted GPA: (4.0*3.0 + 3.5*1.5) / 4.5 = 3.83
    _login_as(client, "std2103020", "StudentPass!1")
    my_results = client.get("/api/results/my")
    assert my_results.status_code == 200
    body = my_results.json()
    assert len(body["results"]) == 2
    assert body["total_credits"] == 4.5
    assert body["gpa"] == 3.83

    # Student cannot publish results
    forbidden = client.post(
        "/api/results",
        json={"student_id": student_id, "course_id": c1["id"], "marks": 99.0},
    )
    assert forbidden.status_code == 403
