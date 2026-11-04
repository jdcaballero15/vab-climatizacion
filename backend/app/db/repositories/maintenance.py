import uuid
from collections.abc import Sequence
from datetime import date

from sqlalchemy import ColumnElement, Row, and_, exists, func, or_, select, true
from sqlalchemy.orm import aliased

from app.db.models.catalog import EquipmentType, WorkType
from app.db.models.client import Client, ClientSite
from app.db.models.crew import Crew
from app.db.models.equipment import Equipment
from app.db.models.maintenance import MaintenanceCheckStep, MaintenancePlan
from app.db.models.work_order import WorkOrder
from app.db.repository import BaseRepository
from app.domain.work_order import OPEN_STATUSES

# Plan, equipo, nombre del tipo de equipo, cliente, domicilio, tipo de trabajo, escuadrilla
# (nula sin escuadrilla) y la última orden generada sin cerrar (nula si no hay).
type PlanRow = Row[
    MaintenancePlan, Equipment, str, Client, ClientSite, WorkType, Crew | None, WorkOrder | None
]


class MaintenancePlanRepository(BaseRepository[MaintenancePlan]):
    model = MaintenancePlan

    @staticmethod
    def _active(today: date) -> ColumnElement[bool]:
        return or_(MaintenancePlan.ends_on.is_(None), MaintenancePlan.ends_on > today)

    async def list_rows(
        self,
        *,
        today: date,
        include_ended: bool,
        equipment_id: uuid.UUID | None = None,
        client_id: uuid.UUID | None = None,
    ) -> Sequence[PlanRow]:
        """Planes con lo que muestra la pantalla, por próxima visita."""
        last_open = (
            select(WorkOrder)
            .where(
                WorkOrder.maintenance_plan_id == self.model.id,
                WorkOrder.status.in_(OPEN_STATUSES),
                WorkOrder.deleted_at.is_(None),
            )
            .order_by(WorkOrder.maintenance_due_on.desc())
            .limit(1)
            .lateral()
        )
        open_order = aliased(WorkOrder, last_open)
        stmt = (
            self._select()
            .add_columns(
                Equipment, EquipmentType.name, Client, ClientSite, WorkType, Crew, open_order
            )
            .join(Equipment, Equipment.id == self.model.equipment_id)
            .join(EquipmentType, EquipmentType.id == Equipment.equipment_type_id)
            .join(ClientSite, ClientSite.id == Equipment.client_site_id)
            .join(Client, Client.id == ClientSite.client_id)
            .join(WorkType, WorkType.id == self.model.work_type_id)
            .outerjoin(Crew, Crew.id == self.model.crew_id)
            .outerjoin(open_order, true())
            .order_by(self.model.next_due_on, Equipment.internal_code)
        )
        if not include_ended:
            stmt = stmt.where(self._active(today))
        if equipment_id is not None:
            stmt = stmt.where(self.model.equipment_id == equipment_id)
        if client_id is not None:
            stmt = stmt.where(Client.id == client_id)
        result = await self.session.execute(stmt)
        return result.all()

    async def equipment_has_active_plan(
        self, equipment_id: uuid.UUID, today: date, *, exclude: uuid.UUID | None = None
    ) -> bool:
        conditions = [
            self.model.equipment_id == equipment_id,
            self.model.deleted_at.is_(None),
            self._active(today),
        ]
        if exclude is not None:
            conditions.append(self.model.id != exclude)
        return bool(await self.session.scalar(select(exists().where(and_(*conditions)))))

    async def due_for_update(self, horizon: date) -> Sequence[MaintenancePlan]:
        """Planes con una visita hasta horizon anterior al fin del abono.

        Se bloquean y se saltean los que tiene otra corrida: dos corridas a la vez no
        generan la misma visita.
        """
        stmt = (
            self._select()
            .where(
                self.model.next_due_on <= horizon,
                or_(self.model.ends_on.is_(None), self.model.next_due_on < self.model.ends_on),
            )
            .order_by(self.model.next_due_on)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def by_ids(self, plan_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, MaintenancePlan]:
        if not plan_ids:
            return {}
        result = await self.session.execute(
            self._select(include_deleted=True).where(self.model.id.in_(plan_ids))
        )
        return {plan.id: plan for plan in result.scalars()}


class CheckStepRepository(BaseRepository[MaintenanceCheckStep]):
    model = MaintenanceCheckStep

    async def list_by_status(self, *, include_inactive: bool) -> Sequence[MaintenanceCheckStep]:
        stmt = self._select()
        if not include_inactive:
            stmt = stmt.where(self.model.is_active.is_(True))
        result = await self.session.execute(stmt.order_by(self.model.position, self.model.name))
        return result.scalars().all()

    async def get_by_name(self, name: str) -> MaintenanceCheckStep | None:
        stmt = self._select().where(func.lower(self.model.name) == func.lower(name))
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def next_position(self) -> int:
        stmt = select(func.coalesce(func.max(self.model.position) + 1, 0)).where(
            self.model.deleted_at.is_(None)
        )
        return int((await self.session.execute(stmt)).scalar_one())
