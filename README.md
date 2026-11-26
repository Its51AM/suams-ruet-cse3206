# Smart University Academic Management System (SUAMS)

**Course:** CSE 3206 — Software Engineering Sessional  
**Institution:** Rajshahi University of Engineering & Technology (RUET)

SUAMS is a modular, full-stack academic management web application built with **FastAPI**, **SQLAlchemy**, **SQLite**, **Bootstrap 5**, and **Vanilla JavaScript**, following the **Incremental Development Model** and **Test-Driven Development (TDD)**.

---

## Features & Functional Modules

1. **Authentication & Role Management (`app/core/security.py`, `app/routers/auth.py`)**
   - Role-Based Access Control (RBAC) for `admin`, `teacher`, and `student`.
   - `bcrypt` password hashing and JWT tokens stored in `HttpOnly` cookies.
2. **Student Management (`app/services/student_service.py`, `app/routers/students.py`)**
   - Admin CRUD for student accounts and academic profiles (roll number, department, batch, semester).
   - Search/filter directory and isolated student self-profile (`/profile`).
3. **Course Management (`app/services/course_service.py`, `app/routers/courses.py`)**
   - Course creation, teacher registration & assignment, and duplicate-guarded student enrollment.
4. **Attendance Management (`app/services/attendance_service.py`, `app/routers/attendance.py`)**
   - Assigned teachers record/upsert daily `Present`, `Absent`, or `Late` statuses.
   - Students track course-wise attendance records and overall attendance percentage.
5. **Result & Grade Management (`app/services/result_service.py`, `app/routers/results.py`)**
   - Automated RUET-aligned letter grade (`A+` to `F`) and credit-weighted GPA computation.
6. **Notice & Notification Management (`app/services/notice_service.py`, `app/patterns/`)**
   - Role- and course-scoped announcements paired with **Observer**, **Factory**, and **Adapter** patterns for automated student notifications.

---

## Architecture & Design Patterns

- **SDLC, System Architecture, ER & UML Diagrams:** [docs/sdlc_and_architecture.md](docs/sdlc_and_architecture.md)
- **Functional & Non-Functional Requirements:** [docs/requirements.md](docs/requirements.md)
- **User Stories & Use Cases:** [docs/use_cases.md](docs/use_cases.md)
- **Design Patterns (Factory, Adapter, Observer + UML):** [docs/design_patterns.md](docs/design_patterns.md)
- **Test Plan & Coverage Report:** [docs/test_plan_and_report.md](docs/test_plan_and_report.md)
- **Git & GitHub PR Workflow Guide:** [docs/git_workflow.md](docs/git_workflow.md)
- **GitHub Projects Learning Log:** [docs/github_projects_log.md](docs/github_projects_log.md)

---

## Local Setup & Running the Application

### 1. Create Virtual Environment & Install Dependencies
```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and set a strong `SECRET_KEY`:
```powershell
Copy-Item .env.example .env
```

### 3. Bootstrap Initial Admin User (No Hardcoded Credentials)
```powershell
.venv\Scripts\python -m app.core.bootstrap --username admin --email admin@ruet.ac.bd --full-name "System Admin"
```
*(You will be prompted securely for the admin password, or you may supply `SUAMS_ADMIN_PASSWORD` in your local `.env`.)*

### 4. Start the Web Server
```powershell
.venv\Scripts\python -m uvicorn app.main:app --reload
```
Open `http://127.0.0.1:8000` in your browser (interactive Swagger API docs at `http://127.0.0.1:8000/docs`).

---

## Running Tests & Coverage

### Unit, Mock & Integration Tests (`pytest` + `pytest-cov`)
```powershell
.venv\Scripts\python -m pytest tests/unit tests/integration --cov=app --cov-report=term-missing
```

### Selenium E2E UI Tests (Headless Chrome)
```powershell
.venv\Scripts\python -m pytest tests/ui
```

---

## Manual Verification Walkthrough (By Module)

1. **Auth & RBAC:** Visit `/login`, test an invalid password (error banner appears), then log in as `admin` to access `/dashboard`.
2. **Student Management:** Open `/students`, add a student (e.g., roll `2103001`), filter by department, update semester, and confirm persistence after refresh.
3. **Course Management:** Open `/courses`, register a teacher, create `CSE 3206`, assign the teacher, and enroll the student.
4. **Attendance:** Log in as the teacher, open `/attendance`, select `CSE 3206`, mark `Present`/`Late`/`Absent`, and save.
5. **Results & Grades:** Open `/results` as the teacher, enter marks (e.g., `85`), publish, and confirm `A+` (`4.00`) is calculated.
6. **Notices & Notifications:** Publish an announcement on `/notices`, then log in as the enrolled student to view the Notice Board, personal Notification Inbox (generated via Observer → Factory → Adapter), GPA on `/results`, and attendance rate on `/attendance`.

---

## CI/CD Pipeline

GitHub Actions ([.github/workflows/ci.yml](.github/workflows/ci.yml)) automatically installs dependencies, executes unit/integration tests with `pytest-cov` XML/terminal reporting, runs headless Chrome Selenium UI tests, and uploads JUnit/coverage artifacts on every push and pull request.
