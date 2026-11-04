import uuid
from datetime import date

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
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


class MaintenanceCheckStep(TimestampedBase):
    """Paso del checklist único de mantenimiento, editable por la oficina (E07-01).

    Decisión de Gonza (2026-11-03): una sola lista para todo mantenimiento, sin plantillas
    por frecuencia ni por tipo de equipo. Cada orden generada se guarda una copia de los
    pasos activos (WorkOrderCheckItem): editar la lista no cambia las órdenes ya generadas.
    """

    __tablename__ = "maintenance_check_step"
    __table_args__ = (Index("uq_maintenance_check_step_name", text("lower(name)"), unique=True),)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    # Quitar un paso lo desactiva, no lo borra (E07-01, criterio 4).
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
