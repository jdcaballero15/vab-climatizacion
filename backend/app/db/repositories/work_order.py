import uuid
from collections.abc import Sequence
from datetime import date, datetime

from sqlalchemy import Row, func, select, update

from app.db.models.catalog import EquipmentType, WorkType
from app.db.models.client import Client, ClientSite
from app.db.models.equipment import Equipment
from app.db.models.work_order import WorkOrder, WorkOrderAssignment, WorkOrderEvent
from app.db.repository import BaseRepository
from app.domain.work_order import CREW_OPEN_STATUSES, OrderStatus, WorkOrderEventType

# Orden abierta de una escuadrilla: orden, fecha prevista, cliente, domicilio, tipo de
# trabajo, equipo y nombre de su tipo (estos dos, nulos sin equipo).
type OpenCrewOrderRow = Row[WorkOrder, date, str, ClientSite, str, Equipment | None, str | None]


class WorkOrderRepository(BaseRepository[WorkOrder]):
    model = WorkOrder

    async def update_status_if(
        self, order_id: uuid.UUID, *, expected: OrderStatus, new: OrderStatus
    ) -> bool:
        """Cambia el estado solo si sigue siendo el leído. False si otro lo cambió antes."""
        stmt = (
            update(self.model)
            .where(
                self.model.id == order_id,
                self.model.status == expected,
                self.model.deleted_at.is_(None),
            )
            .values(status=new)
            .returning(self.model.id)
            .execution_options(synchronize_session=False)
        )
        return await self.session.scalar(stmt) is not None

    def add_event(self, event: WorkOrderEvent) -> None:
        self.session.add(event)

    async def list_by_status_page(
        self, status: OrderStatus, *, limit: int, offset: int
    ) -> tuple[Sequence[Row[WorkOrder, datetime, str, str | None, str, str]], int]:
        """Órdenes en un estado, de la más vieja a la más nueva según su evento de creación.

        Cada fila trae la orden, su fecha de creación, el nombre del cliente, el rótulo y
        la dirección del domicilio y el nombre del tipo de trabajo.
        """
        filtered = self._select().where(self.model.status == status)
        total = await self.session.scalar(select(func.count()).select_from(filtered.subquery()))
        stmt = (
            select(
                self.model,
                WorkOrderEvent.occurred_at,
                Client.name,
                ClientSite.label,
                ClientSite.address,
                WorkType.name,
            )
            .join(
                WorkOrderEvent,
                (WorkOrderEvent.work_order_id == self.model.id)
                & (WorkOrderEvent.event_type == WorkOrderEventType.created),
            )
            .join(Client, Client.id == self.model.client_id)
            .join(ClientSite, ClientSite.id == self.model.client_site_id)
            .join(WorkType, WorkType.id == self.model.work_type_id)
            .where(self.model.status == status, self.model.deleted_at.is_(None))
            .order_by(WorkOrderEvent.occurred_at, self.model.number)
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return result.all(), total or 0

    async def list_open_for_crew(
        self, crew_id: uuid.UUID, *, order_id: uuid.UUID | None = None
    ) -> Sequence[OpenCrewOrderRow]:
        """Órdenes Asignada y En curso con la asignación vigente de la escuadrilla.

        Por fecha prevista y número. Cada fila trae la orden, la fecha prevista, el nombre
        del cliente, el domicilio, el nombre del tipo de trabajo, el equipo y el nombre de
        su tipo (estos dos, nulos si la orden no tiene equipo). Con order_id, solo esa orden
        (vacío si no es una orden abierta de la escuadrilla).
        """
        stmt = (
            select(
                self.model,
                WorkOrderAssignment.scheduled_for,
                Client.name,
                ClientSite,
                WorkType.name,
                Equipment,
                EquipmentType.name,
            )
            .join(WorkOrderAssignment, WorkOrderAssignment.work_order_id == self.model.id)
            .join(Client, Client.id == self.model.client_id)
            .join(ClientSite, ClientSite.id == self.model.client_site_id)
            .join(WorkType, WorkType.id == self.model.work_type_id)
            .outerjoin(Equipment, Equipment.id == self.model.equipment_id)
            .outerjoin(EquipmentType, EquipmentType.id == Equipment.equipment_type_id)
            .where(
                WorkOrderAssignment.crew_id == crew_id,
                WorkOrderAssignment.unassigned_at.is_(None),
                WorkOrderAssignment.deleted_at.is_(None),
                self.model.status.in_(CREW_OPEN_STATUSES),
                self.model.deleted_at.is_(None),
            )
            .order_by(WorkOrderAssignment.scheduled_for, self.model.number)
        )
        if order_id is not None:
            stmt = stmt.where(self.model.id == order_id)
        result = await self.session.execute(stmt)
        return result.all()
