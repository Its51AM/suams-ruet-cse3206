# Functional and Non-Functional Requirements — SUAMS

## 1. Functional Requirements (FR)

### Module 1: Authentication and Role Management
- **FR-1.1:** Users shall authenticate using username or email and password (`POST /api/auth/login` and `POST /login`).
- **FR-1.2:** The system shall support three roles: `admin`, `teacher`, and `student`.
- **FR-1.3:** Protected API routes and web pages shall enforce Role-Based Access Control (RBAC), returning HTTP `401` for unauthenticated requests and HTTP `403` for unauthorized roles.
- **FR-1.4:** Users shall be able to log out (`POST /api/auth/logout` and `/logout`), clearing the session cookie.

### Module 2: Student Management
- **FR-2.1:** Admins shall be able to create student accounts and academic profiles (roll number, department, batch year, current semester, phone).
- **FR-2.2:** Admins and Teachers shall be able to view and filter/search the student directory by department, semester, roll number, or name.
- **FR-2.3:** Admins shall be able to update and delete student records; duplicate usernames, emails, or roll numbers shall be rejected.
- **FR-2.4:** Students shall be able to view their own profile (`/api/students/me`, `/profile`) and shall be blocked from reading other students' profiles.

### Module 3: Course Management
- **FR-3.1:** Admins shall be able to register teachers and create, update, and delete courses (`course_code`, `title`, `credits`, `semester`, `department`, `teacher_id`).
- **FR-3.2:** Admins shall be able to assign teachers to courses and enroll students in courses.
- **FR-3.3:** Students shall be able to browse courses and self-register without duplicate enrollments.
- **FR-3.4:** Teachers shall be able to view courses assigned to them and the enrolled student roster.

### Module 4: Attendance Management
- **FR-4.1:** Teachers shall be able to record daily attendance (`Present`, `Absent`, `Late`) for students enrolled in courses assigned to them.
- **FR-4.2:** Updating attendance for the same `(student_id, course_id, attendance_date)` shall upsert the existing record rather than creating duplicates.
- **FR-4.3:** Students shall be able to view their attendance history and calculated attendance percentage (`(Present + Late) / Total * 100`).

### Module 5: Result and Grade Management
- **FR-5.1:** Assigned teachers (or admins) shall be able to publish or update marks (`0.0` to `100.0`) for enrolled students.
- **FR-5.2:** The system shall automatically compute RUET-aligned letter grades (`A+` down to `F`) and grade points (`4.00` down to `0.00`) as well as credit-weighted GPA.
- **FR-5.3:** Students shall be able to view only their own published results and GPA.

### Module 6: Notice and Announcement Management
- **FR-6.1:** Admins and Teachers shall be able to publish announcements targeted at `all`, `student`, or `teacher`, optionally scoped to a specific course.
- **FR-6.2:** Users shall view notices matching their role on the Notice Board and Dashboard.
- **FR-6.3:** Publishing a notice or result shall trigger the Observer pattern to create student notifications through Factory-instantiated Adapter services.

---

## 2. Non-Functional Requirements (NFR)

1. **Security:**
   - Passwords hashed with `bcrypt` (`app/core/security.py`).
   - Session tokens signed with JWT (`HS256`) stored in `HttpOnly`, `SameSite=Lax` cookies.
   - `SECRET_KEY` loaded from environment variables (`.env`), never hardcoded in source files.
   - All request payloads validated via Pydantic v2 schemas; SQLite queries parameterized via SQLAlchemy ORM.
2. **Data Integrity & Persistence:**
   - All domain records stored persistently in SQLite with `PRAGMA foreign_keys=ON`.
   - Composite unique constraints on `enrollments`, `attendance_records`, and `results`.
3. **Maintainability & Extensibility:**
   - Layered separation (`routers` → `services` → `patterns` → `models`) enables isolated unit testing with `unittest.mock` and adding new notification channels without modifying core services.
4. **Usability:**
   - Responsive Bootstrap 5 UI with role-tailored navigation and clear inline validation/flash feedback.
5. **Testability & CI:**
   - TDD workflow using `pytest`, `unittest.mock`, `pytest-cov`, and headless Selenium UI tests automated via GitHub Actions.
