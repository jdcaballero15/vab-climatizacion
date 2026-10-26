import uuid
from collections.abc import Sequence

from sqlalchemy import exists, func, select

from app.db.models.crew import Crew, FieldTechnician
from app.db.models.work_order import WorkOrder, WorkOrderAssignment
from app.db.repository import BaseRepository
from app.domain.work_order import CREW_OPEN_STATUSES


class CrewRepository(BaseRepository[Crew]):
    model = Crew

    async def list_by_status(self, *, include_inactive: bool) -> Sequence[Crew]:
        stmt = self._select().order_by(self.model.is_active.desc(), func.lower(self.model.name))
        if not include_inactive:
            stmt = stmt.where(self.model.is_active.is_(True))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_name(self, name: str) -> Crew | None:
        """Busca sin distinguir mayúsculas, activas e inactivas (misma regla que el índice)."""
        stmt = self._select().where(func.lower(self.model.name) == func.lower(name))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_app_user(self, user_id: uuid.UUID) -> Crew | None:
        stmt = self._select(include_deleted=True).where(self.model.app_user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def has_open_orders(self, crew_id: uuid.UUID) -> bool:
        """Si tiene alguna orden Asignada o En curso con su asignación vigente."""
        stmt = select(
            exists().where(
                WorkOrderAssignment.crew_id == crew_id,
                WorkOrderAssignment.unassigned_at.is_(None),
                WorkOrderAssignment.deleted_at.is_(None),
                WorkOrder.id == WorkOrderAssignment.work_order_id,
                WorkOrder.status.in_(CREW_OPEN_STATUSES),
                WorkOrder.deleted_at.is_(None),
            )
        )
        return bool(await self.session.scalar(stmt))


class FieldTechnicianRepository(BaseRepository[FieldTechnician]):
    model = FieldTechnician

    async def list_by_status(self, *, include_inactive: bool) -> Sequence[FieldTechnician]:
        stmt = self._select().order_by(
            self.model.is_active.desc(), func.lower(self.model.full_name)
        )
        if not include_inactive:
            stmt = stmt.where(self.model.is_active.is_(True))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_name(self, full_name: str) -> FieldTechnician | None:
        stmt = self._select().where(func.lower(self.model.full_name) == func.lower(full_name))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
