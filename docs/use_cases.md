# User Stories and Use Case Documentation — SUAMS

## 1. User Stories

| ID | Role | User Story | Acceptance Criteria |
| :--- | :--- | :--- | :--- |
| **US-01** | Admin | As an Admin, I want to log in securely and manage student records so that student enrollment data stays accurate. | Admin can add, search, update semester, and delete students; duplicates return an error. |
| **US-02** | Admin | As an Admin, I want to create courses and assign teachers so that academic offerings are structured by semester. | Course code uniqueness enforced; teacher dropdown lists registered teachers. |
| **US-03** | Teacher | As a Teacher, I want to mark and update daily attendance for my assigned courses so that student participation is tracked. | Only assigned teacher (or admin) can save attendance; duplicate date rows are prevented. |
| **US-04** | Teacher | As a Teacher, I want to publish marks for my students so that grades and GPA are computed automatically. | Marks in `[0, 100]` map to letter grade + grade point and notify the student. |
| **US-05** | Admin/Teacher | As an Admin or Teacher, I want to publish notices so that target students receive timely announcements. | Notice appears on Notice Board and generates notifications for target recipients. |
| **US-06** | Student | As a Student, I want to register for courses and inspect my attendance, GPA, and notifications in one portal. | Student sees only own attendance/results, can enroll once per course, and mark alerts read. |

---

## 2. Detailed Use Case Descriptions

### UC-01: Authenticate User and Enforce RBAC
- **Actors:** Admin, Teacher, Student
- **Preconditions:** Active account exists in `users`.
- **Main Flow:**
  1. User navigates to `/login` and submits username/email and password.
  2. `AuthService.authenticate_user` retrieves the user and verifies the bcrypt hash.
  3. System creates a JWT token, sets `suams_access_token` (`HttpOnly`) cookie, and redirects to `/dashboard`.
- **Alternative Flow:** Invalid password or inactive account returns HTTP `401` with an inline alert.

### UC-02: Register and Manage Student Profile
- **Actors:** Admin (Manage), Student (View Own Profile)
- **Preconditions:** Admin is authenticated.
- **Main Flow:**
  1. Admin submits student details on `/students`.
  2. `StudentService.create_student` validates unique username, email, and roll number, hashes password, and commits `User` + `Student`.
  3. Student appears in the directory table.
- **Exception Flow:** Duplicate roll number or email raises `ValueError` and flashes an error banner.

### UC-03: Create Course, Assign Teacher, and Enroll Student
- **Actors:** Admin, Student
- **Preconditions:** Teacher and Student accounts exist.
- **Main Flow:**
  1. Admin creates a course and selects an assigned teacher.
  2. Student clicks **Enroll** on `/courses` (or Admin enrolls the student).
  3. `CourseService.enroll_student` verifies no existing `(student_id, course_id)` pair and creates an `Enrollment`.
- **Exception Flow:** Second enrollment attempt returns HTTP `400` ("already enrolled").

### UC-04: Record Daily Course Attendance
- **Actors:** Teacher (assigned), Student (viewer)
- **Preconditions:** Teacher is assigned to the course; students are enrolled.
- **Main Flow:**
  1. Teacher opens `/attendance`, picks a course and date, and loads the enrolled roster.
  2. Teacher selects `Present`, `Absent`, or `Late` per student and clicks **Save Attendance**.
  3. `AttendanceService.record_attendance` upserts records for `(student_id, course_id, attendance_date)`.
- **Exception Flow:** Unassigned teacher receives HTTP `403`.

### UC-05: Publish Results and Calculate Grades
- **Actors:** Teacher (assigned), Student (viewer)
- **Preconditions:** Student is enrolled in the course.
- **Main Flow:**
  1. Teacher opens `/results`, enters marks `[0, 100]` for a student, and clicks **Publish**.
  2. `GradeCalculator.calculate_grade` derives letter grade & grade point.
  3. `ResultService.publish_result` saves the `Result` and triggers `AcademicEventPublisher.notify("result_published", ...)`.
  4. Student views updated GPA on `/results` and sees the alert in `/notices`.

### UC-06: Publish Notice and Deliver Notifications
- **Actors:** Admin, Teacher, Student
- **Preconditions:** Author has `admin` or `teacher` role.
- **Main Flow:**
  1. Author fills title, audience (`all`/`student`/`teacher`), optional course, and content.
  2. `NoticeService.publish_notice` saves `Notice` and emits `notice_published` to `StudentNotificationObserver`.
  3. Observer fetches an `INotificationService` from `NotificationFactory` and persists `Notification` entries.
