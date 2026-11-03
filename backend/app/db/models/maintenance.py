import uuid
from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Integer, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TimestampedBase


class MaintenancePlan(TimestampedBase):
    """Plan de mantenimiento de un equipo abonado (E07-03, decisión de Gonza 2026-11-03).

    Cada every_months meses toca una visita; una semana antes de next_due_on el sistema
    genera la orden y corre la fecha (E07-04). ends_on es el día desde el que ya no se
    generan visitas (E07-03, criterio 2): desde ahí el plan queda como historial.
    """

    __tablename__ = "maintenance_plan"
    __table_args__ = (
        CheckConstraint("every_months BETWEEN 1 AND 24", name="ck_maintenance_plan_every"),
        # Un equipo en un solo plan sin fin (criterio 3); los que tienen fin futuro los
        # controla el servicio.
        Index(
            "uq_maintenance_plan_open_equipment",
            "equipment_id",
            unique=True,
            postgresql_where=text("ends_on IS NULL AND deleted_at IS NULL"),
        ),
    )

    equipment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("equipment.id"), nullable=False, index=True
    )
    work_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("work_type.id"), nullable=False)
    # La que suele ir: viene elegida al asignar, pero la orden nace Pendiente.
    crew_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("crew.id"), nullable=True)
    every_months: Mapped[int] = mapped_column(Integer, nullable=False)
    next_due_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
