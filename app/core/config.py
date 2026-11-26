"""Application configuration loaded from environment variables."""

from functools import lru_cache
import secrets
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration settings for SUAMS."""

    app_name: str = "Smart University Academic Management System (SUAMS)"
    environment: str = "development"
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 120
    database_url: str = "sqlite:///./suams.db"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_sender: str = "noreply@suams.ruet.ac.bd"
    cookie_secure: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("secret_key", mode="before")
    @classmethod
    def ensure_secret_key(cls, value: str | None) -> str:
        """Use configured SECRET_KEY or generate an ephemeral runtime key for dev/test."""
        if value and str(value).strip():
            return str(value).strip()
        return secrets.token_urlsafe(32)


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    settings = Settings()
    if settings.environment.lower() == "production" and not settings.secret_key:
        raise ValueError("SECRET_KEY must be explicitly configured in production.")
    return settings
