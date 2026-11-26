"""Selenium E2E UI tests for SUAMS web interface."""

import socket
import threading
import time
import pytest
from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from sqlalchemy.orm import sessionmaker
import uvicorn
from app.core.database import Base, create_db_engine, get_db
from app.main import create_app
from app.models.user import UserRole
from app.services.auth_service import AuthService


pytestmark = pytest.mark.ui


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def live_server_url(tmp_path_factory):
    """Run a real Uvicorn + FastAPI instance backed by an isolated SQLite DB."""
    db_dir = tmp_path_factory.mktemp("ui_db")
    db_path = db_dir / "suams_ui.db"
    engine = create_db_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(bind=engine)
    UISessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with UISessionLocal() as session:
        AuthService.create_user(
            session,
            username="ui_admin",
            email="ui_admin@ruet.ac.bd",
            full_name="UI Admin",
            password="UiAdminPass!1",
            role=UserRole.ADMIN,
        )

    app = create_app(init_db=False)

    def override_get_db():
        db = UISessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    port = _find_free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for server socket readiness
    deadline = time.time() + 10.0
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                break
        except OSError:
            time.sleep(0.1)

    yield f"http://127.0.0.1:{port}"

    server.should_exit = True
    thread.join(timeout=5)
    engine.dispose()


@pytest.fixture(scope="module")
def browser():
    """Create a headless Chrome WebDriver (falling back to Edge if needed)."""
    options = ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1366,900")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(5)
    yield driver
    driver.quit()


def _click_and_wait_reload(browser, wait: WebDriverWait, element) -> None:
    """Click a submit/navigation element and wait until the new document finishes loading."""
    old_html = browser.find_element(By.TAG_NAME, "html")
    element.click()

    def _reloaded(driver) -> bool:
        try:
            _ = old_html.tag_name
            return False
        except (StaleElementReferenceException, WebDriverException):
            return driver.execute_script("return document.readyState") == "complete"

    wait.until(_reloaded)


def test_suams_end_to_end_ui_journey(live_server_url, browser):
    """Verify login, student creation, course creation, notice publishing, and student login via browser."""
    wait = WebDriverWait(
        browser, 10, ignored_exceptions=(StaleElementReferenceException, WebDriverException)
    )

    # 1. Unauthenticated access redirects to login
    browser.get(f"{live_server_url}/dashboard")
    wait.until(EC.presence_of_element_located((By.ID, "login-form")))

    # 2. Invalid credentials show error alert
    browser.find_element(By.ID, "identifier").send_keys("ui_admin")
    browser.find_element(By.ID, "password").send_keys("WrongPass!")
    _click_and_wait_reload(browser, wait, browser.find_element(By.ID, "login-submit-btn"))
    error_el = wait.until(EC.presence_of_element_located((By.ID, "login-error")))
    assert "Invalid" in error_el.text

    # 3. Valid Admin login
    browser.find_element(By.ID, "identifier").clear()
    browser.find_element(By.ID, "identifier").send_keys("ui_admin")
    browser.find_element(By.ID, "password").clear()
    browser.find_element(By.ID, "password").send_keys("UiAdminPass!1")
    _click_and_wait_reload(browser, wait, browser.find_element(By.ID, "login-submit-btn"))

    wait.until(lambda d: d.find_element(By.ID, "current-user-role").text.strip().upper() == "ADMIN")

    # 4. Create a student via UI
    browser.get(f"{live_server_url}/students")
    wait.until(EC.presence_of_element_located((By.ID, "add-student-form")))
    browser.find_element(By.ID, "student-full-name").send_keys("Tariqul Islam")
    browser.find_element(By.ID, "student-username").send_keys("std2103050")
    browser.find_element(By.ID, "student-roll").send_keys("2103050")
    browser.find_element(By.ID, "student-email").send_keys("2103050@student.ruet.ac.bd")
    browser.find_element(By.ID, "student-password").send_keys("StudentUiPass!1")
    _click_and_wait_reload(browser, wait, browser.find_element(By.ID, "create-student-btn"))

    wait.until(
        lambda d: "2103050" in d.find_element(By.ID, "students-table").text
        and "Tariqul Islam" in d.find_element(By.ID, "students-table").text
    )

    # 5. Create a course via UI
    browser.get(f"{live_server_url}/courses")
    wait.until(EC.presence_of_element_located((By.ID, "create-course-form")))
    browser.find_element(By.ID, "course-code").send_keys("CSE 3206")
    browser.find_element(By.ID, "course-title").send_keys("Software Engineering Sessional")
    _click_and_wait_reload(browser, wait, browser.find_element(By.ID, "create-course-btn"))

    wait.until(lambda d: "CSE 3206" in d.find_element(By.ID, "courses-table").text)

    # 6. Publish a notice via UI
    browser.get(f"{live_server_url}/notices")
    wait.until(EC.presence_of_element_located((By.ID, "publish-notice-form")))
    browser.find_element(By.ID, "notice-title").send_keys("Project Defense Schedule")
    browser.find_element(By.ID, "notice-content").send_keys("CSE 3206 project defense starts at 9:30 AM.")
    _click_and_wait_reload(browser, wait, browser.find_element(By.ID, "publish-notice-btn"))
    wait.until(lambda d: "Project Defense Schedule" in d.page_source)

    # 7. Logout and log in as the newly created student
    _click_and_wait_reload(browser, wait, browser.find_element(By.ID, "logout-btn"))
    wait.until(EC.presence_of_element_located((By.ID, "login-form")))

    browser.find_element(By.ID, "identifier").send_keys("std2103050")
    browser.find_element(By.ID, "password").send_keys("StudentUiPass!1")
    _click_and_wait_reload(browser, wait, browser.find_element(By.ID, "login-submit-btn"))

    wait.until(lambda d: d.find_element(By.ID, "current-user-role").text.strip().upper() == "STUDENT")

    # Student enrolls in CSE 3206 from UI and sees notice notification
    browser.get(f"{live_server_url}/courses")
    enroll_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "form[action*='enroll-self'] button")))
    _click_and_wait_reload(browser, wait, enroll_btn)
    wait.until(lambda d: "Enrolled" in d.find_element(By.ID, "courses-table").text)

    browser.get(f"{live_server_url}/notices")
    wait.until(lambda d: "Project Defense Schedule" in d.page_source)
