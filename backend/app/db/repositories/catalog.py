import uuid
from collections.abc import Sequence

from sqlalchemy import func

from app.db.models.catalog import EquipmentType, Task, WorkType
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
