import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import TimestampedBase
from app.db.models.user import User


class Crew(TimestampedBase):
    """Escuadrilla (D-013): lista fija con nombre; las personas que la forman cambian.

    Tiene el usuario del celular con el que entra a la app (rol técnico).
    """

    __tablename__ = "crew"
    # Nombre ya normalizado (sin espacios sobrantes); lower() hace que no distinga
    # mayúsculas, también contra las inactivas.
    __table_args__ = (Index("uq_crew_name", text("lower(name)"), unique=True),)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    app_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("app_user.id"), unique=True, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    app_user: Mapped[User | None] = relationship(lazy="joined")


class FieldTechnician(TimestampedBase):
    """Persona de campo (D-013). No tiene usuario: se tilda al cerrar las órdenes."""

    __tablename__ = "field_technician"
    __table_args__ = (
        Index("uq_field_technician_full_name", text("lower(full_name)"), unique=True),
    )

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
