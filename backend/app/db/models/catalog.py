import uuid

from sqlalchemy import Boolean, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.db.base import TimestampedBase

# Valor que ocupa el lugar de "sin tipo de equipo" en los índices únicos de fallas y reparaciones.
GENERIC_SCOPE = "00000000-0000-0000-0000-000000000000"


class WorkType(TimestampedBase):
    """Tipo de trabajo de una orden (instalación, reparación, service, etc.)."""

    __tablename__ = "work_type"
    # El nombre se guarda ya normalizado (sin espacios sobrantes); lower() hace que
    # la unicidad no distinga mayúsculas, también contra los inactivos.
    __table_args__ = (Index("uq_work_type_name", text("lower(name)"), unique=True),)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # El cierre pide falla y reparación solo en los tipos marcados (E02-10).
    requires_failure_repair: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
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
    # Prefijo del código interno de sus equipos (D-002). Sin prefijo, el código usa "EO".
    code_prefix: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class EquipmentScopedCatalog(TimestampedBase):
    """Valor de catálogo de un tipo de equipo, o genérico (sin tipo) que aplica a todos."""

    __abstract__ = True

    @declared_attr.directive
    @classmethod
    def __table_args__(cls) -> tuple[Index]:
        # Mismo nombre dentro del mismo alcance (un tipo, o las genéricas entre sí). El cruce
        # entre genéricas y específicas no entra en un índice y lo chequea el servicio.
        return (
            Index(
                f"uq_{cls.__tablename__}_scope_name",
                text(f"coalesce(equipment_type_id, '{GENERIC_SCOPE}'::uuid)"),
                text("lower(name)"),
                unique=True,
            ),
        )

    equipment_type_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("equipment_type.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Failure(EquipmentScopedCatalog):
    """Falla predefinida que el técnico elige al cerrar."""

    __tablename__ = "failure"


class Repair(EquipmentScopedCatalog):
    """Reparación predefinida que el técnico elige al cerrar, dentro de una falla."""

    __tablename__ = "repair"

    failure_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("failure.id"), nullable=False, index=True
    )
