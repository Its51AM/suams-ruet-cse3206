"""FastAPI application entrypoint and factory for SUAMS."""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config import get_settings
from app.core.database import Base, engine
import app.models  # noqa: F401 - ensure all ORM models are registered
from app.routers.attendance import router as attendance_router
from app.routers.auth import router as auth_router
from app.routers.courses import router as courses_router
from app.routers.notices import router as notices_router
from app.routers.results import router as results_router
from app.routers.students import router as students_router
from app.routers.views import router as views_router

BASE_DIR = Path(__file__).resolve().parent


def create_app(init_db: bool = True) -> FastAPI:
    """Create and configure the SUAMS FastAPI application."""
    settings = get_settings()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if init_db:
            Base.metadata.create_all(bind=engine)
        yield

    application = FastAPI(title=settings.app_name, lifespan=lifespan)

    static_dir = BASE_DIR / "static"
    if static_dir.exists():
        application.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    application.include_router(views_router)
    application.include_router(auth_router)
    application.include_router(students_router)
    application.include_router(courses_router)
    application.include_router(attendance_router)
    application.include_router(results_router)
    application.include_router(notices_router)

    @application.get("/health", tags=["System"])
    def health_check():
        return {"status": "healthy", "app": settings.app_name}

    return application


app = create_app()
