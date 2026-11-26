"""Server-rendered HTML views router for SUAMS Bootstrap UI."""

from datetime import date
from pathlib import Path
from urllib.parse import quote
from fastapi import APIRouter, Depends, Form, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    COOKIE_NAME,
    create_access_token,
    get_optional_current_user,
)
from app.models.attendance import AttendanceStatus
from app.models.notice import Notice
from app.models.user import Student, Teacher, User, UserRole
from app.patterns.observer import build_default_publisher
from app.schemas.attendance import AttendanceEntry
from app.schemas.course import CourseCreate, TeacherCreate
from app.schemas.notice import NoticeCreate
from app.schemas.student import StudentCreate, StudentUpdate
from app.services.attendance_service import AttendanceService
from app.services.auth_service import AuthService
from app.services.course_service import CourseService
from app.services.notice_service import NoticeService
from app.services.result_service import ResultService
from app.services.student_service import StudentService

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(tags=["Web UI"])


def _redirect_login() -> RedirectResponse:
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


def _flash_redirect(url: str, message: str, variant: str = "success") -> RedirectResponse:
    sep = "&" if "?" in url else "?"
    return RedirectResponse(
        url=f"{url}{sep}msg={quote(message)}&variant={quote(variant)}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


def _base_ctx(request: Request, user: User | None, active_page: str) -> dict:
    return {
        "request": request,
        "user": user,
        "active_page": active_page,
        "flash_message": request.query_params.get("msg"),
        "flash_variant": request.query_params.get("variant", "success"),
    }


@router.get("/", response_class=HTMLResponse)
def home(user: User | None = Depends(get_optional_current_user)):
    """Redirect authenticated users to dashboard and guests to login."""
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return _redirect_login()


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user: User | None = Depends(get_optional_current_user)):
    """Render the login form."""
    if user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(request, "login.html", {"user": None, "error": None})


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    identifier: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """Authenticate form login and set HttpOnly JWT session cookie."""
    user = AuthService.authenticate_user(db, identifier, password)
    if not user:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"user": None, "error": "Invalid username/email or password."},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    settings = get_settings()
    token = create_access_token({"sub": user.username, "role": user.role})
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.access_token_expire_minutes * 60,
    )
    return response


@router.post("/logout")
@router.get("/logout")
def logout_page():
    """Clear session cookie and redirect to login."""
    response = _redirect_login()
    response.delete_cookie(key=COOKIE_NAME)
    return response


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
):
    """Render role-tailored dashboard KPIs, notices, and notifications."""
    if not user:
        return _redirect_login()

    notices = NoticeService.list_notices(db, role=user.role)
    notifications = NoticeService.list_user_notifications(db, user.id)
    unread_count = sum(1 for n in notifications if not n.is_read)

    stats: dict = {"notice_count": len(notices), "unread_notifications": unread_count}
    if user.role == UserRole.ADMIN.value:
        stats["student_count"] = db.query(Student).count()
        stats["teacher_count"] = db.query(Teacher).count()
        stats["course_count"] = len(CourseService.list_courses(db))
    elif user.role == UserRole.TEACHER.value:
        teacher = db.query(Teacher).filter(Teacher.user_id == user.id).first()
        courses = CourseService.list_courses(db, teacher_id=teacher.id) if teacher else []
        stats["course_count"] = len(courses)
    else:
        student = StudentService.get_student_by_user_id(db, user.id)
        courses = CourseService.list_student_courses(db, student.id) if student else []
        att = AttendanceService.get_student_attendance_summary(db, student.id) if student else {"attendance_percentage": 0.0}
        transcript = ResultService.get_student_transcript(db, student.id) if student else {"gpa": 0.0}
        stats["course_count"] = len(courses)
        stats["attendance_percentage"] = att["attendance_percentage"]
        stats["gpa"] = transcript["gpa"]

    ctx = _base_ctx(request, user, "dashboard")
    ctx.update({"stats": stats, "notices": notices, "notifications": notifications})
    return templates.TemplateResponse(request, "dashboard.html", ctx)


@router.get("/students", response_class=HTMLResponse)
def students_page(
    request: Request,
    search: str | None = Query(default=None),
    department: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
):
    """Render Student Directory (Admin & Teacher)."""
    if not user:
        return _redirect_login()
    if user.role == UserRole.STUDENT.value:
        return RedirectResponse(url="/profile", status_code=status.HTTP_303_SEE_OTHER)

    students = StudentService.list_students(db, department=department, search=search)
    ctx = _base_ctx(request, user, "students")
    ctx.update({"students": students, "search": search, "department": department})
    return templates.TemplateResponse(request, "students.html", ctx)


@router.post("/students/create")
def create_student_form(
    username: str = Form(...),
    email: str = Form(...),
    full_name: str = Form(...),
    password: str = Form(...),
    roll_number: str = Form(...),
    department: str = Form(...),
    batch_year: int = Form(...),
    current_semester: int = Form(...),
    phone: str | None = Form(default=None),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
):
    """Handle Admin student creation form."""
    if not user or user.role != UserRole.ADMIN.value:
        return _redirect_login()
    try:
        StudentService.create_student(
            db,
            StudentCreate(
                username=username,
                email=email,
                full_name=full_name,
                password=password,
                roll_number=roll_number,
                department=department,
                batch_year=batch_year,
                current_semester=current_semester,
                phone=phone or None,
            ),
        )
        return _flash_redirect("/students", f"Student {roll_number} created successfully.")
    except Exception as exc:
        return _flash_redirect("/students", str(exc), "danger")


@router.post("/students/{student_id}/update")
def update_student_form(
    student_id: int,
    current_semester: int = Form(...),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
):
    """Handle Admin inline student semester update."""
    if not user or user.role != UserRole.ADMIN.value:
        return _redirect_login()
    try:
        StudentService.update_student(db, student_id, StudentUpdate(current_semester=current_semester))
        return _flash_redirect("/students", "Student updated.")
    except Exception as exc:
        return _flash_redirect("/students", str(exc), "danger")


@router.post("/students/{student_id}/delete")
def delete_student_form(
    student_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
):
    """Handle Admin student deletion."""
    if not user or user.role != UserRole.ADMIN.value:
        return _redirect_login()
    StudentService.delete_student(db, student_id)
    return _flash_redirect("/students", "Student deleted.")


@router.get("/profile", response_class=HTMLResponse)
def student_profile_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
):
    """Render authenticated student's profile page."""
    if not user:
        return _redirect_login()
    student = StudentService.get_student_by_user_id(db, user.id)
    courses = CourseService.list_student_courses(db, student.id) if student else []
    ctx = _base_ctx(request, user, "profile")
    ctx.update({"student": student, "courses": courses})
    return templates.TemplateResponse(request, "profile.html", ctx)


@router.get("/courses", response_class=HTMLResponse)
def courses_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
):
    """Render courses catalog and role-specific actions."""
    if not user:
        return _redirect_login()

    teachers = CourseService.list_teachers(db)
    students = StudentService.list_students(db) if user.role == UserRole.ADMIN.value else []
    enrolled_course_ids: set[int] = set()

    if user.role == UserRole.TEACHER.value:
        teacher = db.query(Teacher).filter(Teacher.user_id == user.id).first()
        courses = CourseService.list_courses(db, teacher_id=teacher.id) if teacher else []
    else:
        courses = CourseService.list_courses(db)
        if user.role == UserRole.STUDENT.value:
            student = StudentService.get_student_by_user_id(db, user.id)
            if student:
                enrolled_course_ids = {c.id for c in CourseService.list_student_courses(db, student.id)}

    ctx = _base_ctx(request, user, "courses")
    ctx.update(
        {
            "courses": courses,
            "teachers": teachers,
            "students": students,
            "enrolled_course_ids": enrolled_course_ids,
        }
    )
    return templates.TemplateResponse(request, "courses.html", ctx)


@router.post("/courses/create")
def create_course_form(
    course_code: str = Form(...),
    title: str = Form(...),
    credits: float = Form(...),
    semester: int = Form(...),
    department: str = Form(...),
    teacher_id: str = Form(default=""),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
):
    """Handle Admin course creation form."""
    if not user or user.role != UserRole.ADMIN.value:
        return _redirect_login()
    try:
        parsed_teacher_id = int(teacher_id) if teacher_id.strip() else None
        CourseService.create_course(
            db,
            CourseCreate(
                course_code=course_code,
                title=title,
                credits=credits,
                semester=semester,
                department=department,
                teacher_id=parsed_teacher_id,
            ),
        )
        return _flash_redirect("/courses", f"Course {course_code.upper()} created.")
    except Exception as exc:
        return _flash_redirect("/courses", str(exc), "danger")


@router.post("/courses/teachers/create")
def create_teacher_form(
    full_name: str = Form(...),
    username: str = Form(...),
    employee_id: str = Form(...),
    email: str = Form(...),
    department: str = Form(...),
    designation: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
):
    """Handle Admin teacher creation form."""
    if not user or user.role != UserRole.ADMIN.value:
        return _redirect_login()
    try:
        CourseService.create_teacher(
            db,
            TeacherCreate(
                full_name=full_name,
                username=username,
                employee_id=employee_id,
                email=email,
                department=department,
                designation=designation,
                password=password,
            ),
        )
        return _flash_redirect("/courses", f"Teacher {full_name} registered.")
    except Exception as exc:
        return _flash_redirect("/courses", str(exc), "danger")


@router.post("/courses/enroll")
def enroll_student_admin_form(
    course_id: int = Form(...),
    student_id: int = Form(...),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
):
    """Handle Admin student enrollment into a course."""
    if not user or user.role != UserRole.ADMIN.value:
        return _redirect_login()
    try:
        CourseService.enroll_student(db, course_id=course_id, student_id=student_id)
        return _flash_redirect("/courses", "Student enrolled successfully.")
    except Exception as exc:
        return _flash_redirect("/courses", str(exc), "danger")


@router.post("/courses/{course_id}/enroll-self")
def enroll_self_form(
    course_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
):
    """Handle Student self-registration in a course."""
    if not user or user.role != UserRole.STUDENT.value:
        return _redirect_login()
    student = StudentService.get_student_by_user_id(db, user.id)
    if not student:
        return _flash_redirect("/courses", "Student profile missing.", "danger")
    try:
        CourseService.enroll_student(db, course_id=course_id, student_id=student.id)
        return _flash_redirect("/courses", "Enrolled in course successfully.")
    except Exception as exc:
        return _flash_redirect("/courses", str(exc), "danger")


@router.post("/courses/{course_id}/delete")
def delete_course_form(
    course_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
):
    """Handle Admin course deletion."""
    if not user or user.role != UserRole.ADMIN.value:
        return _redirect_login()
    CourseService.delete_course(db, course_id)
    return _flash_redirect("/courses", "Course deleted.")


@router.get("/attendance", response_class=HTMLResponse)
def attendance_page(
    request: Request,
    course_id: int | None = Query(default=None),
    attendance_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
):
    """Render attendance marking (Teacher/Admin) or attendance summary (Student)."""
    if not user:
        return _redirect_login()

    ctx = _base_ctx(request, user, "attendance")
    target_date = attendance_date or date.today()

    if user.role == UserRole.STUDENT.value:
        student = StudentService.get_student_by_user_id(db, user.id)
        summary = (
            AttendanceService.get_student_attendance_summary(db, student.id)
            if student
            else {
                "total_classes": 0,
                "present_count": 0,
                "late_count": 0,
                "absent_count": 0,
                "attendance_percentage": 0.0,
                "records": [],
            }
        )
        ctx.update({"summary": summary})
        return templates.TemplateResponse(request, "attendance.html", ctx)

    if user.role == UserRole.TEACHER.value:
        teacher = db.query(Teacher).filter(Teacher.user_id == user.id).first()
        courses = CourseService.list_courses(db, teacher_id=teacher.id) if teacher else []
    else:
        courses = CourseService.list_courses(db)

    selected_course = None
    if courses:
        selected_course = next((c for c in courses if c.id == course_id), courses[0])

    roster = CourseService.list_course_students(db, selected_course.id) if selected_course else []
    existing_records = (
        AttendanceService.get_course_attendance(db, selected_course.id, attendance_date=target_date)
        if selected_course
        else []
    )
    existing_map = {rec.student_id: rec.status for rec in existing_records}

    ctx.update(
        {
            "courses": courses,
            "selected_course": selected_course,
            "attendance_date": target_date.isoformat(),
            "roster": roster,
            "existing_map": existing_map,
        }
    )
    return templates.TemplateResponse(request, "attendance.html", ctx)


@router.post("/attendance/save")
async def save_attendance_form(
    request: Request,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
):
    """Persist batch attendance statuses submitted from the HTML roster form."""
    if not user or user.role not in (UserRole.ADMIN.value, UserRole.TEACHER.value):
        return _redirect_login()

    form = await request.form()
    course_id = int(form["course_id"])
    att_date = date.fromisoformat(str(form["attendance_date"]))

    entries: list[AttendanceEntry] = []
    for key, value in form.items():
        if key.startswith("status_"):
            student_id = int(key.split("_", 1)[1])
            entries.append(AttendanceEntry(student_id=student_id, status=AttendanceStatus(str(value))))

    if not entries:
        return _flash_redirect(f"/attendance?course_id={course_id}&attendance_date={att_date}", "No students to mark.", "warning")

    try:
        AttendanceService.record_attendance(
            db,
            course_id=course_id,
            attendance_date=att_date,
            entries=entries,
            marked_by_user_id=user.id,
        )
        return _flash_redirect(
            f"/attendance?course_id={course_id}&attendance_date={att_date}",
            "Attendance saved successfully.",
        )
    except Exception as exc:
        return _flash_redirect(f"/attendance?course_id={course_id}", str(exc), "danger")


@router.get("/results", response_class=HTMLResponse)
def results_page(
    request: Request,
    course_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
):
    """Render marks publishing (Teacher/Admin) or student transcript (Student)."""
    if not user:
        return _redirect_login()

    ctx = _base_ctx(request, user, "results")
    if user.role == UserRole.STUDENT.value:
        student = StudentService.get_student_by_user_id(db, user.id)
        transcript = (
            ResultService.get_student_transcript(db, student.id)
            if student
            else {"total_credits": 0.0, "gpa": 0.0, "results": []}
        )
        ctx.update({"transcript": transcript})
        return templates.TemplateResponse(request, "results.html", ctx)

    if user.role == UserRole.TEACHER.value:
        teacher = db.query(Teacher).filter(Teacher.user_id == user.id).first()
        courses = CourseService.list_courses(db, teacher_id=teacher.id) if teacher else []
    else:
        courses = CourseService.list_courses(db)

    selected_course = next((c for c in courses if c.id == course_id), courses[0]) if courses else None
    roster = CourseService.list_course_students(db, selected_course.id) if selected_course else []
    published = ResultService.get_course_results(db, selected_course.id) if selected_course else []
    result_map = {r.student_id: r for r in published}

    ctx.update(
        {
            "courses": courses,
            "selected_course": selected_course,
            "roster": roster,
            "result_map": result_map,
        }
    )
    return templates.TemplateResponse(request, "results.html", ctx)


@router.post("/results/publish")
def publish_result_form(
    course_id: int = Form(...),
    student_id: int = Form(...),
    marks: float = Form(...),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
):
    """Publish student marks from the grading sheet form and notify student."""
    if not user or user.role not in (UserRole.ADMIN.value, UserRole.TEACHER.value):
        return _redirect_login()
    try:
        publisher = build_default_publisher()
        res = ResultService.publish_result(
            db,
            student_id=student_id,
            course_id=course_id,
            marks=marks,
            publisher=publisher,
        )
        return _flash_redirect(
            f"/results?course_id={course_id}",
            f"Published {res.letter_grade} ({res.marks} marks) and notified student.",
        )
    except Exception as exc:
        return _flash_redirect(f"/results?course_id={course_id}", str(exc), "danger")


@router.get("/notices", response_class=HTMLResponse)
def notices_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
):
    """Render announcement board and personal notification inbox."""
    if not user:
        return _redirect_login()

    notices = NoticeService.list_notices(db, role=user.role)
    notifications = NoticeService.list_user_notifications(db, user.id)
    courses = CourseService.list_courses(db) if user.role in (UserRole.ADMIN.value, UserRole.TEACHER.value) else []

    ctx = _base_ctx(request, user, "notices")
    ctx.update({"notices": notices, "notifications": notifications, "courses": courses})
    return templates.TemplateResponse(request, "notices.html", ctx)


@router.post("/notices/create")
def create_notice_form(
    title: str = Form(...),
    target_role: str = Form("all"),
    course_id: str = Form(default=""),
    content: str = Form(...),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
):
    """Publish a notice via HTML form and trigger Observer notifications."""
    if not user or user.role not in (UserRole.ADMIN.value, UserRole.TEACHER.value):
        return _redirect_login()
    try:
        parsed_course_id = int(course_id) if course_id.strip() else None
        publisher = build_default_publisher()
        NoticeService.publish_notice(
            db,
            payload=NoticeCreate(
                title=title,
                content=content,
                target_role=target_role,  # type: ignore[arg-type]
                course_id=parsed_course_id,
            ),
            author_id=user.id,
            publisher=publisher,
        )
        return _flash_redirect("/notices", "Announcement published and subscribers notified.")
    except Exception as exc:
        return _flash_redirect("/notices", str(exc), "danger")


@router.post("/notices/notifications/{notification_id}/read")
def mark_notification_read_form(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_current_user),
):
    """Mark a personal notification as read from the UI."""
    if not user:
        return _redirect_login()
    try:
        NoticeService.mark_notification_read(db, notification_id, user.id)
        return _flash_redirect("/notices", "Notification marked as read.")
    except LookupError:
        return _flash_redirect("/notices", "Notification not found.", "danger")
