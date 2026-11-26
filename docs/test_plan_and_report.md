# Test Plan and Test Report — SUAMS

## 1. Testing Strategy

SUAMS applies **Test-Driven Development (TDD)** across three complementary layers:
1. **Unit & Mock Tests (`tests/unit/`):** Verify pure business rules (`GradeCalculator`, password hashing, JWT roundtrips) and isolate SQLAlchemy/external services via `unittest.mock.MagicMock`.
2. **Integration Tests (`tests/integration/`):** Exercise FastAPI endpoints, SQLAlchemy ORM constraints, HTML view routes, and bootstrap helpers against an isolated in-memory SQLite database.
3. **End-to-End UI Tests (`tests/ui/`):** Drive a real headless Google Chrome browser via Selenium WebDriver against a live Uvicorn server (`127.0.0.1`).

---

## 2. Test Case Matrix & Observed Results

| Test ID | Module | Test Case Description | Expected Result | Actual Result | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-01** | Auth & Security | Hash and verify password with bcrypt | Hash differs from plaintext; valid password verifies `True`, invalid `False` | Verified as expected | **PASS** |
| **TC-02** | Auth & Security | Encode/decode JWT and reject tampered token | Valid token decodes `sub`/`role`; invalid raises `401` | Verified as expected | **PASS** |
| **TC-03** | Auth & RBAC | `AuthService` with mocked DB rejects inactive users | Returns `User` when active, `None` when inactive | Verified as expected | **PASS** |
| **TC-04** | Auth & RBAC | API login, RBAC (`403` for student on admin check), logout | Cookie issued on login, `403` enforced, `401` after logout | Verified as expected | **PASS** |
| **TC-05** | Student Mgmt | Mocked DB `get_student_by_id` + full CRUD & roll uniqueness | Admin CRUD succeeds; duplicate roll returns `400`; cross-student access `403` | Verified as expected | **PASS** |
| **TC-06** | Course Mgmt | Mocked DB duplicate enrollment guard + course/enroll API flow | Duplicate enrollment raises `ValueError` / `400`; teacher roster shows enrolled student | Verified as expected | **PASS** |
| **TC-07** | Attendance | Mocked summary calculation + upsert attendance & `403` guard | Same-date resubmission updates without duplicate; `75.0%` / `50.0%` accurate | Verified as expected | **PASS** |
| **TC-08** | Results & Grades | Parametrized RUET scale (`A+`..`F`), invalid range, weighted GPA | All 10 grade tiers pass; out-of-range raises `ValueError`; GPA `3.83` accurate | Verified as expected | **PASS** |
| **TC-09** | Patterns (Factory) | `NotificationFactory` creates adapters and rejects unknown channel | Returns `InAppNotificationAdapter` / `EmailNotificationAdapter`; raises `ValueError` | Verified as expected | **PASS** |
| **TC-10** | Patterns (Adapter) | `EmailNotificationAdapter` delegates to mocked `ExternalEmailClient` | `dispatch_email` called once with mapped arguments and logged to DB | Verified as expected | **PASS** |
| **TC-11** | Patterns (Observer) | `AcademicEventPublisher` attach/detach + end-to-end notice/result alerts | Attached observers notified; publishing notice/result creates student notifications | Verified as expected | **PASS** |
| **TC-12** | Integration | Scoped course notices, HTML forms, and `bootstrap_admin` | Course notice notifies only enrolled student; form routes and bootstrap succeed | Verified as expected | **PASS** |
| **TC-13** | Selenium UI | Full browser journey: login error, Admin CRUD, notice, Student login & enroll | All UI interactions and DOM assertions pass in headless Chrome | Verified as expected | **PASS** |

---

## 3. Observed Execution Summary

- **Unit & Integration Suite (`pytest tests/unit tests/integration --cov=app --cov-report=term-missing`):**
  - **Result:** `31 passed, 1 warning in 66.23s`
  - **Total Statement Coverage:** **83%** (`1496` statements, `250` missed — primarily unexercised error-redirect branches in `app/routers/views.py` and CLI arg parsing in `app/core/bootstrap.py`).
  - **Core Domain & Pattern Coverage Highlights:**
    - `app/models/*`: **100%**
    - `app/schemas/*`: **100%**
    - `app/patterns/factory.py`: **100%**
    - `app/patterns/observer.py`: **98%**
    - `app/patterns/adapters.py`: **94%**
    - `app/services/auth_service.py`: **97%**
    - `app/services/attendance_service.py`: **96%**
    - `app/services/notice_service.py`: **94%**
    - `app/routers/auth.py`: **100%**

- **Selenium UI Suite (`pytest tests/ui`):**
  - **Result:** `1 passed, 1 warning in 70.78s` (`tests/ui/test_suams_ui.py::test_suams_end_to_end_ui_journey`)
