"""Integration tests covering end-to-end API workflows, HTML views, and bootstrap."""

from datetime import date
import pytest
from app.core.bootstrap import bootstrap_admin
from app.models.user import UserRole
from app.services.auth_service import AuthService


pytestmark = pytest.mark.integration


def _login(client, identifier: str, password: str) -> None:
    resp = client.post("/api/auth/login", json={"identifier": identifier, "password": password})
    assert resp.status_code == 200


def test_teacher_creation_course_update_delete_and_scoped_notice(client, db_session):
    """Verify full API lifecycle including course-scoped notices and notification read state."""
    AuthService.create_user(
        db_session,
        username="admin",
        email="admin@ruet.ac.bd",
        full_name="System Admin",
        password="AdminPass!1",
        role=UserRole.ADMIN,
    )
    _login(client, "admin", "AdminPass!1")

    # Create teacher via API
    t_resp = client.post(
        "/api/courses/teachers",
        json={
            "username": "prof_salam",
            "email": "salam@ruet.ac.bd",
            "full_name": "Dr. Abdus Salam",
            "password": "TeacherPass!1",
            "employee_id": "EMP-301",
            "department": "CSE",
            "designation": "Professor",
        },
    )
    assert t_resp.status_code == 201
    teacher_id = t_resp.json()["id"]
    assert len(client.get("/api/courses/teachers").json()) == 1

    # Create two students, enroll only student 1
    s1_resp = client.post(
        "/api/students",
        json={
            "username": "std_one",
            "email": "s1@student.ruet.ac.bd",
            "full_name": "Student One",
            "password": "StudentPass!1",
            "roll_number": "2103101",
            "department": "CSE",
            "batch_year": 2021,
            "current_semester": 6,
        },
    )
    assert s1_resp.status_code == 201
    s1 = s1_resp.json()

    s2_resp = client.post(
        "/api/students",
        json={
            "username": "std_two",
            "email": "s2@student.ruet.ac.bd",
            "full_name": "Student Two",
            "password": "StudentPass!1",
            "roll_number": "2103102",
            "department": "CSE",
            "batch_year": 2021,
            "current_semester": 6,
        },
    )
    assert s2_resp.status_code == 201
    s2 = s2_resp.json()

    course = client.post(
        "/api/courses",
        json={
            "course_code": "CSE 3209",
            "title": "Database Systems",
            "credits": 3.0,
            "semester": 6,
            "department": "CSE",
            "teacher_id": teacher_id,
        },
    ).json()
    assert client.put(f"/api/courses/{course['id']}", json={"title": "Advanced Database Systems"}).status_code == 200
    assert client.post(f"/api/courses/{course['id']}/enroll", json={"student_id": s1["id"]}).status_code == 201

    # Teacher publishes course-scoped notice -> only student 1 gets notification
    _login(client, "prof_salam", "TeacherPass!1")
    notice = client.post(
        "/api/notices",
        json={
            "title": "Lab Quiz 2",
            "content": "SQL normalization quiz tomorrow.",
            "target_role": "student",
            "course_id": course["id"],
        },
    )
    assert notice.status_code == 201

    # Teacher marks attendance & views course attendance & results
    att = client.post(
        f"/api/attendance/courses/{course['id']}",
        json={
            "attendance_date": date(2026, 11, 25).isoformat(),
            "entries": [{"student_id": s1["id"], "status": "Late"}],
        },
    )
    assert att.status_code == 200
    assert len(client.get(f"/api/attendance/courses/{course['id']}").json()) == 1

    assert client.post(
        "/api/results",
        json={"student_id": s1["id"], "course_id": course["id"], "marks": 76.0},
    ).status_code == 200
    assert len(client.get(f"/api/results/courses/{course['id']}").json()) == 1

    # Student 1 has notifications and can mark one as read
    _login(client, "std_one", "StudentPass!1")
    s1_notifs = client.get("/api/notices/notifications/my").json()
    assert len(s1_notifs) == 2
    read_resp = client.post(f"/api/notices/notifications/{s1_notifs[0]['id']}/read")
    assert read_resp.status_code == 200
    assert read_resp.json()["is_read"] is True

    # Student 2 received 0 course-scoped notifications
    _login(client, "std_two", "StudentPass!1")
    assert len(client.get("/api/notices/notifications/my").json()) == 0

    # Admin deletes notice and course
    _login(client, "admin", "AdminPass!1")
    assert client.delete(f"/api/notices/{notice.json()['id']}").status_code == 200
    assert client.delete(f"/api/courses/{course['id']}").status_code == 200


def test_html_views_and_form_workflows(client, db_session):
    """Verify server-rendered HTML pages and form POST workflows."""
    AuthService.create_user(
        db_session,
        username="admin",
        email="admin@ruet.ac.bd",
        full_name="Admin",
        password="AdminPass!1",
        role=UserRole.ADMIN,
    )

    assert client.get("/health").json()["status"] == "healthy"
    assert client.get("/login").status_code == 200

    # Form login with bad credentials returns 401
    bad = client.post("/login", data={"identifier": "admin", "password": "bad"})
    assert bad.status_code == 401

    # Form login with valid credentials redirects to dashboard
    good = client.post("/login", data={"identifier": "admin", "password": "AdminPass!1"})
    assert good.status_code == 200
    assert "Dashboard" in good.text

    # Admin form actions
    assert client.post(
        "/students/create",
        data={
            "username": "u_std1",
            "email": "ustd1@student.ruet.ac.bd",
            "full_name": "UI Student",
            "password": "StudentPass!1",
            "roll_number": "2103099",
            "department": "CSE",
            "batch_year": "2021",
            "current_semester": "6",
        },
    ).status_code == 200

    assert client.post(
        "/courses/create",
        data={
            "course_code": "CSE 3211",
            "title": "Compiler Design",
            "credits": "3.0",
            "semester": "6",
            "department": "CSE",
            "teacher_id": "",
        },
    ).status_code == 200

    assert client.post(
        "/notices/create",
        data={
            "title": "Orientation",
            "target_role": "all",
            "course_id": "",
            "content": "Welcome to Fall semester.",
        },
    ).status_code == 200

    assert client.get("/students").status_code == 200
    assert client.get("/courses").status_code == 200
    assert client.get("/attendance").status_code == 200
    assert client.get("/results").status_code == 200
    assert client.get("/notices").status_code == 200
    assert client.get("/logout").status_code == 200


def test_bootstrap_admin_helper(tmp_path, monkeypatch):
    """Verify bootstrap_admin creates an admin idempotently without hardcoded secrets."""
    db_file = tmp_path / "boot.db"
    from app.core import database as db_mod
    from app.core import bootstrap as boot_mod

    test_engine = db_mod.create_db_engine(f"sqlite:///{db_file}")
    TestingSession = db_mod.sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    monkeypatch.setattr(boot_mod, "engine", test_engine)
    monkeypatch.setattr(boot_mod, "SessionLocal", TestingSession)

    bootstrap_admin("bootadmin", "boot@ruet.ac.bd", "Boot Admin", "BootPass!123")
    bootstrap_admin("bootadmin", "boot@ruet.ac.bd", "Boot Admin", "BootPass!123")

    with TestingSession() as session:
        user = AuthService.authenticate_user(session, "bootadmin", "BootPass!123")
        assert user is not None
        assert user.role == "admin"

    test_engine.dispose()
