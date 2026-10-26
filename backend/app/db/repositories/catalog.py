import uuid
from collections.abc import Sequence

from sqlalchemy import ColumnElement, func, or_

from app.db.models.catalog import (
    EquipmentScopedCatalog,
    EquipmentType,
    Failure,
    Repair,
    Task,
    WorkType,
)
from app.db.repository import BaseRepository


class WorkTypeRepository(BaseRepository[WorkType]):
    model = WorkType

    async def list_by_status(self, *, include_inactive: bool) -> Sequence[WorkType]:
        stmt = self._select().order_by(self.model.name)
        if not include_inactive:
            stmt = stmt.where(self.model.is_active.is_(True))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_name(self, name: str) -> WorkType | None:
        """Busca sin distinguir mayúsculas, activos e inactivos (misma regla que el índice)."""
        stmt = self._select().where(func.lower(self.model.name) == func.lower(name))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class TaskRepository(BaseRepository[Task]):
    model = Task

    async def list_for_work_type(
        self, work_type_id: uuid.UUID, *, include_inactive: bool
    ) -> Sequence[Task]:
        stmt = self._select().where(self.model.work_type_id == work_type_id)
        if not include_inactive:
            stmt = stmt.where(self.model.is_active.is_(True))
        result = await self.session.execute(stmt.order_by(self.model.name))
        return result.scalars().all()

    async def get_by_name(self, work_type_id: uuid.UUID, name: str) -> Task | None:
        stmt = self._select().where(
            self.model.work_type_id == work_type_id,
            func.lower(self.model.name) == func.lower(name),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class EquipmentTypeRepository(BaseRepository[EquipmentType]):
    model = EquipmentType

    async def list_by_status(self, *, include_inactive: bool) -> Sequence[EquipmentType]:
        stmt = self._select().order_by(self.model.name)
        if not include_inactive:
            stmt = stmt.where(self.model.is_active.is_(True))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_name(self, name: str) -> EquipmentType | None:
        """Busca sin distinguir mayúsculas, activos e inactivos (misma regla que el índice)."""
        stmt = self._select().where(func.lower(self.model.name) == func.lower(name))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class EquipmentScopedRepository[ModelT: EquipmentScopedCatalog](BaseRepository[ModelT]):
    """Catálogos de un tipo de equipo o genéricos: fallas y reparaciones."""

    async def list_filtered(
        self,
        *,
        equipment_type_id: uuid.UUID | None,
        include_specific: bool,
        include_inactive: bool,
        extra_filters: Sequence[ColumnElement[bool]] = (),
    ) -> Sequence[ModelT]:
        """Sin tipo, todos los valores. Con tipo, los genéricos y, si se piden, los de ese tipo."""
        stmt = self._select()
        if equipment_type_id is not None:
            scope: ColumnElement[bool] = self.model.equipment_type_id.is_(None)
            if include_specific:
                scope = or_(scope, self.model.equipment_type_id == equipment_type_id)
            stmt = stmt.where(scope)
        if not include_inactive:
            stmt = stmt.where(self.model.is_active.is_(True))
        stmt = stmt.where(*extra_filters)
        result = await self.session.execute(stmt.order_by(self.model.name))
        return result.scalars().all()

    async def find_conflicting(
        self, name: str, equipment_type_id: uuid.UUID | None
    ) -> Sequence[ModelT]:
        """Valores, activos o no, cuyo nombre choca: uno genérico choca con cualquiera;
        uno específico, con los de su tipo y con los genéricos."""
        stmt = self._select().where(func.lower(self.model.name) == func.lower(name))
        if equipment_type_id is not None:
            stmt = stmt.where(
                or_(
                    self.model.equipment_type_id.is_(None),
                    self.model.equipment_type_id == equipment_type_id,
                )
            )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class FailureRepository(EquipmentScopedRepository[Failure]):
    model = Failure


class RepairRepository(EquipmentScopedRepository[Repair]):
    model = Repair
