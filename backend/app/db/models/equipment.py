import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
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


class EquipmentTransfer(TimestampedBase):
    """Traslado de un equipo a otro cliente (E03-09): cambia de código y no se borra nada.

    Las órdenes anteriores siguen siendo del cliente de origen.
    """

    __tablename__ = "equipment_transfer"

    equipment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment.id"), nullable=False, index=True
    )
    from_client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    from_site_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client_site.id"), nullable=False)
    from_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    to_client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client.id"), nullable=False)
    to_site_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("client_site.id"), nullable=False)
    to_code: Mapped[str] = mapped_column(String(50), nullable=False)
    transferred_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    transferred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
