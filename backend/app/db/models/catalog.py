import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TimestampedBase


class WorkType(TimestampedBase):
    """Tipo de trabajo de una orden (instalación, reparación, service, etc.)."""

    __tablename__ = "work_type"
    # El nombre se guarda ya normalizado (sin espacios sobrantes); lower() hace que
    # la unicidad no distinga mayúsculas, también contra los inactivos.
    __table_args__ = (Index("uq_work_type_name", text("lower(name)"), unique=True),)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Task(TimestampedBase):
    """Subtarea predefinida de un tipo de trabajo."""

    __tablename__ = "task"
    __table_args__ = (
        Index("uq_task_work_type_name", "work_type_id", text("lower(name)"), unique=True),
    )

    work_type_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_type.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class EquipmentType(TimestampedBase):
    """Tipo de equipo (split, cámara frigorífica, etc.). Clasifica equipos, fallas y checklists."""

    __tablename__ = "equipment_type"
    __table_args__ = (Index("uq_equipment_type_name", text("lower(name)"), unique=True),)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
