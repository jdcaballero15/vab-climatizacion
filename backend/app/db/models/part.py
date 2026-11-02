import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TimestampedBase


class Part(TimestampedBase):
    """Material (repuesto) que la escuadrilla elige al cerrar (E02-05). En código, "part"."""

    __tablename__ = "part"
    # Como los catálogos: nombre normalizado y único sin distinguir mayúsculas.
    __table_args__ = (Index("uq_part_name", text("lower(name)"), unique=True),)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unidad", server_default="unidad"
    )
    # Hoy los materiales no tienen código; queda opcional.
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class PartPrice(TimestampedBase):
    """Precio de lista de un material desde una fecha (E02-06). Nunca se edita: se agrega.

    El vigente es el último por valid_from. ADMIN: el técnico nunca lo ve.
    """

    __tablename__ = "part_price"
    __table_args__ = (CheckConstraint("list_price >= 0", name="ck_part_price_list_price"),)

    part_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("part.id"), nullable=False, index=True)
    list_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Nulo en la carga inicial por script, que no tiene usuario.
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"), nullable=True)
