import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TimestampedBase


class Equipment(TimestampedBase):
    """Equipo de un cliente, en uno de sus domicilios (D-002)."""

    __tablename__ = "equipment"

    client_site_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("client_site.id"), nullable=False, index=True
    )
    equipment_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment_type.id"), nullable=False, index=True
    )
    # Lo genera el sistema y no se edita. Texto sin largo fijo: los migrados de Persat no
    # siguen un formato parejo, por eso la unicidad la da el índice y no el formato.
    internal_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    # Lo que reconocen el técnico y el cliente ("Habitación 12"); se muestra primero.
    location_note: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
