# SDLC, System Architecture, and Diagrams — SUAMS

## 1. Software Development Life Cycle: Incremental Development Model

SUAMS follows the **Incremental Development Model**, delivering the system in vertical, test-verified increments:

1. **Increment 0:** Core configuration, SQLAlchemy/SQLite engine, Pytest & CI setup.
2. **Increment 1:** Authentication & RBAC (`feature/authentication`).
3. **Increment 2:** Student Management (`feature/student-management`).
4. **Increment 3:** Course & Enrollment Management (`feature/course-management`).
5. **Increment 4:** Attendance Management (`feature/attendance`).
6. **Increment 5:** Result & Grade Management (`feature/results`).
7. **Increment 6:** Notices & Notification System using Factory, Adapter, and Observer (`feature/notifications`).
8. **Increment 7:** Expanded Integration Tests, Selenium UI Suite, Coverage Audit & Documentation (`test/unit-tests`, `docs/project-documentation`).

### Why Incremental Development Fits SUAMS
- **Dependency-ordered delivery:** Auth and Student profiles naturally precede Enrollment, Attendance, and Results.
- **Continuous verification:** Every increment runs through TDD (`Red -> Green -> Refactor`) before merging via Pull Request.
- **Reduced integration risk:** Complex cross-cutting patterns (Observer + Factory + Adapter) are integrated cleanly after domain models stabilize.

---

## 2. System Architecture

```mermaid
flowchart TB
    Browser["Browser: Bootstrap 5 / HTML5 / CSS3 / JS"] --> Routers["FastAPI Routers (views, auth, students, courses, attendance, results, notices)"]
    Routers --> Security["JWT Cookie & RBAC Dependencies (app/core/security.py)"]
    Routers --> Schemas["Pydantic v2 Schemas (app/schemas/)"]
    Routers --> Services["Domain Services (app/services/)"]
    Services --> Patterns["Design Patterns: Observer -> Factory -> Adapter (app/patterns/)"]
    Services --> ORM["SQLAlchemy 2.0 ORM Models (app/models/)"]
    Patterns --> ORM
    ORM --> SQLite[("SQLite Database (suams.db)")]
```

---

## 3. Database Entity-Relationship (ER) Diagram

```mermaid
erDiagram
    USERS ||--o| STUDENTS : "has profile"
    USERS ||--o| TEACHERS : "has profile"
    TEACHERS ||--o{ COURSES : "teaches"
    STUDENTS ||--o{ ENROLLMENTS : "registers"
    COURSES ||--o{ ENROLLMENTS : "contains"
    STUDENTS ||--o{ ATTENDANCE_RECORDS : "has"
    COURSES ||--o{ ATTENDANCE_RECORDS : "tracks"
    STUDENTS ||--o{ RESULTS : "earns"
    COURSES ||--o{ RESULTS : "evaluates"
    USERS ||--o{ NOTICES : "publishes"
    COURSES ||--o{ NOTICES : "scoped to"
    USERS ||--o{ NOTIFICATIONS : "receives"

    USERS {
        int id PK
        string username UK
        string email UK
        string full_name
        string password_hash
        string role
        bool is_active
        datetime created_at
    }
    STUDENTS {
        int id PK
        int user_id FK, UK
        string roll_number UK
        string department
        int batch_year
        int current_semester
        string phone
    }
    TEACHERS {
        int id PK
        int user_id FK, UK
        string employee_id UK
        string department
        string designation
    }
    COURSES {
        int id PK
        string course_code UK
        string title
        float credits
        int semester
        string department
        int teacher_id FK
    }
    ENROLLMENTS {
        int id PK
        int student_id FK
        int course_id FK
        datetime enrolled_at
    }
    ATTENDANCE_RECORDS {
        int id PK
        int student_id FK
        int course_id FK
        date attendance_date
        string status
        int marked_by FK
    }
    RESULTS {
        int id PK
        int student_id FK
        int course_id FK
        float marks
        string letter_grade
        float grade_point
        datetime published_at
    }
    NOTICES {
        int id PK
        string title
        text content
        string target_role
        int course_id FK
        int author_id FK
        datetime created_at
    }
    NOTIFICATIONS {
        int id PK
        int user_id FK
        string channel
        string subject
        text message
        bool is_read
        datetime created_at
    }
```

---

## 4. UML Class Diagram

```mermaid
classDiagram
    class User {
        +int id
        +str username
        +str email
        +str role
    }
    class Student {
        +int id
        +str roll_number
        +str department
        +int current_semester
    }
    class Teacher {
        +int id
        +str employee_id
        +str department
    }
    class Course {
        +int id
        +str course_code
        +str title
        +float credits
    }
    class GradeCalculator {
        +calculate_grade(marks: float) tuple
        +calculate_gpa(results: list) tuple
    }
    class ResultService {
        +publish_result(db, student_id, course_id, marks, publisher) Result
    }
    class NoticeService {
        +publish_notice(db, payload, author_id, publisher) Notice
    }

    User "1" -- "0..1" Student
    User "1" -- "0..1" Teacher
    Teacher "1" -- "0..*" Course
    ResultService --> GradeCalculator : uses
```
