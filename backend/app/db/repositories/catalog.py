import uuid
from collections.abc import Sequence

from sqlalchemy import ColumnElement, func, or_

from app.db.models.catalog import EquipmentType, Failure, Task, WorkType
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


class FailureRepository(BaseRepository[Failure]):
    model = Failure

    async def list_filtered(
        self,
        *,
        equipment_type_id: uuid.UUID | None,
        include_specific: bool,
        include_inactive: bool,
    ) -> Sequence[Failure]:
        """Sin tipo, todas las fallas. Con tipo, las genéricas más (si se piden) las de ese tipo."""
        stmt = self._select()
        if equipment_type_id is not None:
            scope: ColumnElement[bool] = self.model.equipment_type_id.is_(None)
            if include_specific:
                scope = or_(scope, self.model.equipment_type_id == equipment_type_id)
            stmt = stmt.where(scope)
        if not include_inactive:
            stmt = stmt.where(self.model.is_active.is_(True))
        result = await self.session.execute(stmt.order_by(self.model.name))
        return result.scalars().all()

    async def find_conflicting(
        self, name: str, equipment_type_id: uuid.UUID | None
    ) -> Sequence[Failure]:
        """Fallas, activas o no, cuyo nombre choca: una genérica choca con cualquiera;
        una específica, con las de su tipo y con las genéricas."""
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
