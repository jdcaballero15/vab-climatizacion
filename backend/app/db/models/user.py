from enum import StrEnum

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TimestampedBase


class UserRole(StrEnum):
    admin = "admin"
    technician = "technician"
    owner = "owner"


class User(TimestampedBase):
    """Usuario del sistema (tabla app_user). Hereda id y timestamps de la base."""

    __tablename__ = "app_user"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
