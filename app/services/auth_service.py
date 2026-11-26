"""Authentication and user creation business logic."""

from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole


class AuthService:
    """Service encapsulating credential validation and user registration."""

    @staticmethod
    def get_user_by_identifier(db: Session, identifier: str) -> User | None:
        """Fetch a user matching either username or email."""
        normalized = identifier.strip()
        return (
            db.query(User)
            .filter(or_(User.username == normalized, User.email == normalized))
            .first()
        )

    @staticmethod
    def authenticate_user(db: Session, identifier: str, password: str) -> User | None:
        """Validate user credentials and active status."""
        user = AuthService.get_user_by_identifier(db, identifier)
        if not user or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    @staticmethod
    def create_user(
        db: Session,
        *,
        username: str,
        email: str,
        full_name: str,
        password: str,
        role: UserRole,
        is_active: bool = True,
    ) -> User:
        """Create a new user with a securely hashed password."""
        clean_username = username.strip()
        clean_email = email.strip().lower()
        existing = (
            db.query(User)
            .filter(or_(User.username == clean_username, User.email == clean_email))
            .first()
        )
        if existing:
            raise ValueError("A user with this username or email already exists.")

        user = User(
            username=clean_username,
            email=clean_email,
            full_name=full_name.strip(),
            password_hash=hash_password(password),
            role=role.value if isinstance(role, UserRole) else str(role),
            is_active=is_active,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
