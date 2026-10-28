import uuid
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any

from sqlalchemy import ColumnElement, Row, func, select, true, update
from sqlalchemy.orm import InstrumentedAttribute, aliased

from app.db.models.catalog import EquipmentType, Task, WorkType
from app.db.models.client import Client, ClientSite
from app.db.models.crew import Crew, FieldTechnician
from app.db.models.equipment import Equipment
from app.db.models.stored_file import StoredFile
from app.db.models.user import User
from app.db.models.work_order import (
    WorkOrder,
    WorkOrderAssignment,
    WorkOrderCancellation,
    WorkOrderClosure,
    WorkOrderClosurePhoto,
    WorkOrderClosureTask,
    WorkOrderClosureTechnician,
    WorkOrderEvent,
)
from app.db.repository import BaseRepository
from app.domain.work_order import CREW_OPEN_STATUSES, OrderStatus, WorkOrderEventType

# Orden abierta de una escuadrilla: orden, fecha prevista, cliente, domicilio, tipo de
# trabajo, equipo y nombre de su tipo (estos dos, nulos sin equipo).
type OpenCrewOrderRow = Row[WorkOrder, date, str, ClientSite, str, Equipment | None, str | None]
# Orden en un estado: orden, fecha de creación, cliente, rótulo y dirección del domicilio,
# tipo de trabajo, su último cierre; fecha, escuadrilla (nombre e id) y fecha prevista de
# su última asignación; su cancelación y quién canceló (nulos si no tiene).
type StatusOrderRow = Row[
    WorkOrder,
    datetime,
    str,
    str | None,
    str,
    str,
    WorkOrderClosure | None,
    datetime | None,
    str | None,
    uuid.UUID | None,
    date | None,
    WorkOrderCancellation | None,
    str | None,
]


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
    ) -> tuple[Sequence[StatusOrderRow], int]:
        """Órdenes en un estado, en el orden en que se las trabaja.

        Pendientes, de la más vieja a la más nueva según su evento de creación; Asignadas
        y En curso, por fecha prevista; terminadas y canceladas, la última primero.

        Cada fila trae además el último cierre de la orden y su última asignación (para
        saber si volvió de una escuadrilla, E05-08, o a quién está asignada) y su
        cancelación (E04-07).
        """
        filtered = self._select().where(self.model.status == status)
        total = await self.session.scalar(select(func.count()).select_from(filtered.subquery()))
        last_closure = (
            select(WorkOrderClosure)
            .where(WorkOrderClosure.work_order_id == self.model.id)
            .order_by(WorkOrderClosure.closed_at.desc())
            .limit(1)
            .lateral()
        )
        closure = aliased(WorkOrderClosure, last_closure)
        last_assignment = (
            select(
                WorkOrderAssignment.assigned_at,
                WorkOrderAssignment.crew_id,
                WorkOrderAssignment.scheduled_for,
            )
            .where(WorkOrderAssignment.work_order_id == self.model.id)
            .order_by(WorkOrderAssignment.assigned_at.desc())
            .limit(1)
            .lateral()
        )
        cancelled_by = aliased(User)
        order_by: tuple[ColumnElement[Any] | InstrumentedAttribute[Any], ...]
        if status in CREW_OPEN_STATUSES:
            order_by = (last_assignment.c.scheduled_for, self.model.number)
        elif status == OrderStatus.cancelled:
            order_by = (WorkOrderCancellation.cancelled_at.desc(), self.model.number.desc())
        elif status == OrderStatus.done:
            order_by = (closure.closed_at.desc(), self.model.number.desc())
        else:
            order_by = (WorkOrderEvent.occurred_at, self.model.number)
        stmt = (
            select(
                self.model,
                WorkOrderEvent.occurred_at,
                Client.name,
                ClientSite.label,
                ClientSite.address,
                WorkType.name,
                closure,
                last_assignment.c.assigned_at,
                Crew.name,
                last_assignment.c.crew_id,
                last_assignment.c.scheduled_for,
                WorkOrderCancellation,
                cancelled_by.full_name,
            )
            .join(
                WorkOrderEvent,
                (WorkOrderEvent.work_order_id == self.model.id)
                & (WorkOrderEvent.event_type == WorkOrderEventType.created),
            )
            .join(Client, Client.id == self.model.client_id)
            .join(ClientSite, ClientSite.id == self.model.client_site_id)
            .join(WorkType, WorkType.id == self.model.work_type_id)
            .outerjoin(closure, true())
            .outerjoin(last_assignment, true())
            .outerjoin(Crew, Crew.id == last_assignment.c.crew_id)
            .outerjoin(
                WorkOrderCancellation,
                (WorkOrderCancellation.work_order_id == self.model.id)
                & WorkOrderCancellation.deleted_at.is_(None),
            )
            .outerjoin(cancelled_by, cancelled_by.id == WorkOrderCancellation.cancelled_by)
            .where(self.model.status == status, self.model.deleted_at.is_(None))
            .order_by(*order_by)
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

    async def current_assignment(self, order_id: uuid.UUID) -> WorkOrderAssignment | None:
        stmt = select(WorkOrderAssignment).where(
            WorkOrderAssignment.work_order_id == order_id,
            WorkOrderAssignment.unassigned_at.is_(None),
            WorkOrderAssignment.deleted_at.is_(None),
        )
        return await self.session.scalar(stmt)

    async def end_current_assignment(self, order_id: uuid.UUID) -> None:
        """Deja la orden sin escuadrilla: la asignación vigente pasa a histórica."""
        stmt = (
            update(WorkOrderAssignment)
            .where(
                WorkOrderAssignment.work_order_id == order_id,
                WorkOrderAssignment.unassigned_at.is_(None),
                WorkOrderAssignment.deleted_at.is_(None),
            )
            .values(unassigned_at=func.now())
            .execution_options(synchronize_session=False)
        )
        await self.session.execute(stmt)


class WorkOrderClosureRepository(BaseRepository[WorkOrderClosure]):
    model = WorkOrderClosure

    async def get_by_idempotency_key(self, key: uuid.UUID) -> WorkOrderClosure | None:
        stmt = self._select().where(self.model.idempotency_key == key)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def last_for_order(self, order_id: uuid.UUID) -> WorkOrderClosure | None:
        stmt = (
            self._select()
            .where(self.model.work_order_id == order_id)
            .order_by(self.model.closed_at.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def technician_names(self, closure_id: uuid.UUID) -> list[str]:
        stmt = (
            select(FieldTechnician.full_name)
            .join(
                WorkOrderClosureTechnician,
                WorkOrderClosureTechnician.field_technician_id == FieldTechnician.id,
            )
            .where(WorkOrderClosureTechnician.closure_id == closure_id)
            .order_by(FieldTechnician.full_name)
        )
        return list(await self.session.scalars(stmt))

    async def task_names(self, closure_id: uuid.UUID) -> list[str]:
        stmt = (
            select(Task.name)
            .join(WorkOrderClosureTask, WorkOrderClosureTask.task_id == Task.id)
            .where(WorkOrderClosureTask.closure_id == closure_id)
            .order_by(Task.name)
        )
        return list(await self.session.scalars(stmt))

    async def photos(self, closure_id: uuid.UUID) -> list[StoredFile]:
        stmt = (
            select(StoredFile)
            .join(WorkOrderClosurePhoto, WorkOrderClosurePhoto.file_id == StoredFile.id)
            .where(WorkOrderClosurePhoto.closure_id == closure_id)
            .order_by(WorkOrderClosurePhoto.position)
        )
        return list(await self.session.scalars(stmt))

    async def used_photo_ids(self, file_ids: Sequence[uuid.UUID]) -> set[uuid.UUID]:
        """Los archivos de la lista que ya son foto de algún cierre."""
        stmt = select(WorkOrderClosurePhoto.file_id).where(
            WorkOrderClosurePhoto.file_id.in_(file_ids)
        )
        return set(await self.session.scalars(stmt))

    async def crew_name(self, closure: WorkOrderClosure) -> str | None:
        """La escuadrilla de la última asignación anterior al cierre: la que lo hizo."""
        stmt = (
            select(Crew.name)
            .join(WorkOrderAssignment, WorkOrderAssignment.crew_id == Crew.id)
            .where(
                WorkOrderAssignment.work_order_id == closure.work_order_id,
                WorkOrderAssignment.assigned_at <= closure.closed_at,
            )
            .order_by(WorkOrderAssignment.assigned_at.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)
