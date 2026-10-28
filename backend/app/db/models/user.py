import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Uuid, false
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TimestampedBase
from app.domain.user import UserRole

# UserRole vive en el dominio (la máquina de estados lo usa); se re-exporta acá.
__all__ = ["User", "UserRole"]


class User(TimestampedBase):
    """Usuario del sistema (tabla app_user). Hereda id y timestamps de la base."""

    __tablename__ = "app_user"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # E01-05: con una contraseña temporal, la API solo deja cambiarla.
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    # Último restablecimiento (criterio 5); el historial completo llega con la auditoría general.
    password_reset_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    password_reset_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("app_user.id"), nullable=True
    )
