"""CLI bootstrap script to create an initial Admin account without hardcoded secrets."""

import argparse
import getpass
import os
from app.core.database import Base, SessionLocal, engine
import app.models  # noqa: F401
from app.models.user import UserRole
from app.services.auth_service import AuthService


def bootstrap_admin(username: str, email: str, full_name: str, password: str) -> None:
    """Create initial database tables and an admin user if one does not exist."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = AuthService.get_user_by_identifier(db, username) or AuthService.get_user_by_identifier(
            db, email
        )
        if existing:
            print(f"User '{existing.username}' already exists.")
            return
        user = AuthService.create_user(
            db,
            username=username,
            email=email,
            full_name=full_name,
            password=password,
            role=UserRole.ADMIN,
        )
        print(f"Created Admin user '{user.username}' ({user.email}).")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap initial SUAMS Admin account.")
    parser.add_argument("--username", default=os.getenv("SUAMS_ADMIN_USERNAME", "admin"))
    parser.add_argument("--email", default=os.getenv("SUAMS_ADMIN_EMAIL", "admin@ruet.ac.bd"))
    parser.add_argument("--full-name", default=os.getenv("SUAMS_ADMIN_NAME", "System Administrator"))
    parser.add_argument("--password", default=os.getenv("SUAMS_ADMIN_PASSWORD", ""))
    args = parser.parse_args()

    password = args.password or getpass.getpass("Enter initial Admin password: ")
    if len(password) < 6:
        raise SystemExit("Password must be at least 6 characters.")
    bootstrap_admin(args.username, args.email, args.full_name, password)


if __name__ == "__main__":
    main()
