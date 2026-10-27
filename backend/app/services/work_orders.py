import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.client import ClientSiteTechnicianOut, site_map_url
from app.api.schemas.work_order import (
    AssignmentCreate,
    CrewOrdersTechnicianOut,
    CrewTechnicianOut,
    EquipmentTechnicianOut,
    OrderDetailTechnicianOut,
    OrderTechnicianOut,
    PendingOrderOut,
    ReturnedFromCrewOut,
    WorkOrderAdminOut,
    WorkOrderCreate,
)
from app.core.dates import business_today, format_date
from app.db.models.crew import Crew
from app.db.models.user import User
from app.db.models.work_order import (
    WorkOrder,
    WorkOrderAssignment,
    WorkOrderClosure,
    WorkOrderEvent,
)
from app.db.repositories.client import ClientContactRepository
from app.db.repositories.crew import CrewRepository
from app.db.repositories.work_order import OpenCrewOrderRow, WorkOrderRepository
from app.domain.work_order import (
    STATUSLESS_EVENT_TYPES,
    ClosureOutcome,
    OrderAction,
    OrderSource,
    OrderStatus,
    WorkOrderEventType,
    resolve_transition,
)
from app.services import catalog as catalog_service
from app.services import clients as clients_service


class WorkOrderNotFoundError(Exception):
    """No existe una orden activa con ese id."""


class OrderStatusConflictError(Exception):
    """Otro usuario cambió el estado de la orden después de leerla."""

    code = "order_status_conflict"
    message = "La orden cambió mientras la mirabas. Volvé a cargarla e intentá de nuevo."


class WorkTypeInactiveError(Exception):
    """El tipo de trabajo elegido está desactivado."""


class CrewNotAvailableError(Exception):
    """La escuadrilla elegida no existe o está desactivada."""


class ScheduledDateInPastError(Exception):
    """La fecha prevista es anterior a hoy."""


class OrderRequiresApprovalError(Exception):
    """La orden es de un lote de mantenimiento sin aprobar (R6)."""


async def create_work_order(
    session: AsyncSession, data: WorkOrderCreate, actor: User
) -> WorkOrderAdminOut:
    """Alta manual desde administración: queda Pendiente, con su evento de creación."""
    await clients_service.get_client(session, data.client_id)
    await clients_service.check_active_site_of_client(session, data.client_id, data.client_site_id)
    work_type = await catalog_service.get_work_type(session, data.work_type_id)
    if not work_type.is_active:
        raise WorkTypeInactiveError

    order = WorkOrder(status=OrderStatus.pending, source=OrderSource.manual, **data.model_dump())
    session.add(order)
    await session.flush()
    event = WorkOrderEvent(
        work_order_id=order.id,
        event_type=WorkOrderEventType.created,
        to_status=OrderStatus.pending,
        actor_id=actor.id,
    )
    WorkOrderRepository(session).add_event(event)
    await session.commit()
    await session.refresh(order)
    await session.refresh(event)
    return WorkOrderAdminOut.model_validate({**_columns(order), "created_at": event.occurred_at})


async def list_pending(
    session: AsyncSession, *, limit: int, offset: int
) -> tuple[list[PendingOrderOut], int]:
    rows, total = await WorkOrderRepository(session).list_by_status_page(
        OrderStatus.pending, limit=limit, offset=offset
    )
    items = [
        PendingOrderOut(
            id=order.id,
            number=order.number,
            client_id=order.client_id,
            client_name=client_name,
            site_label=site_label,
            site_address=site_address,
            work_type_name=work_type_name,
            description=order.description,
            created_at=created_at,
            returned=_returned(closure, assigned_at, crew_name),
        )
        for (
            order,
            created_at,
            client_name,
            site_label,
            site_address,
            work_type_name,
            closure,
            assigned_at,
            crew_name,
        ) in rows
    ]
    return items, total


def _returned(
    closure: WorkOrderClosure | None, assigned_at: datetime | None, crew_name: str | None
) -> ReturnedFromCrewOut | None:
    """El último cierre explica por qué está Pendiente solo si no se la reasignó después.

    La escuadrilla es la de la última asignación, que es la que terminó ese cierre.
    """
    if closure is None or assigned_at is None or crew_name is None:
        return None
    if closure.outcome == ClosureOutcome.done:
        return None
    if assigned_at > closure.closed_at:
        return None
    return ReturnedFromCrewOut(
        crew_name=crew_name,
        closed_at=closure.closed_at,
        outcome=closure.outcome,
        not_done_reason=closure.not_done_reason,
        observation=closure.observation,
    )


async def list_for_crew_user(session: AsyncSession, user: User) -> CrewOrdersTechnicianOut:
    """Órdenes abiertas de la escuadrilla del usuario del celular (E05-01, D-013).

    La escuadrilla sale del usuario de la sesión. Sin una activa, no ve órdenes.
    """
    today = business_today()
    crew = await active_crew_of(session, user)
    if crew is None:
        return CrewOrdersTechnicianOut(crew=None, today=today, orders=[])

    rows = await WorkOrderRepository(session).list_open_for_crew(crew.id)
    orders = await _technician_orders(session, rows)
    return CrewOrdersTechnicianOut(
        crew=CrewTechnicianOut(name=crew.name), today=today, orders=orders
    )


async def get_for_crew_user(
    session: AsyncSession, user: User, order_id: uuid.UUID
) -> OrderDetailTechnicianOut:
    """Detalle de una orden abierta de la escuadrilla del usuario (E05-02).

    Otra escuadrilla, otro estado, desasignada o inexistente: no se distingue (404).
    """
    crew = await active_crew_of(session, user)
    rows = (
        await WorkOrderRepository(session).list_open_for_crew(crew.id, order_id=order_id)
        if crew is not None
        else []
    )
    if not rows:
        raise WorkOrderNotFoundError
    (order_out,) = await _technician_orders(session, rows)
    order = rows[0][0]
    tasks = await catalog_service.list_tasks(session, order.work_type_id, include_inactive=False)
    return OrderDetailTechnicianOut(
        **order_out.model_dump(),
        requester_area=order.requester_area,
        tasks=[task.name for task in tasks],
        today=business_today(),
    )


async def start_for_crew_user(
    session: AsyncSession, user: User, order_id: uuid.UUID
) -> OrderDetailTechnicianOut:
    """La escuadrilla inicia una orden suya: Asignada pasa a En curso (E05-03).

    Idempotente por estado: si ya está En curso, la devuelve sin otro evento. Mismo
    filtro que el detalle, así que otra escuadrilla o una orden cerrada dan 404.
    """
    detail = await get_for_crew_user(session, user, order_id)
    if detail.status == OrderStatus.in_progress:
        return detail
    order = await get_work_order(session, order_id)
    try:
        await apply_transition(session, order, OrderAction.start, user, None)
    except OrderStatusConflictError:
        # Un doble toque que llegó a la vez: si la otra ya la inició, es el mismo resultado.
        # El conflicto hizo rollback y venció los objetos de la sesión, el usuario incluido.
        await session.refresh(user)
        detail = await get_for_crew_user(session, user, order_id)
        if detail.status != OrderStatus.in_progress:
            raise
        return detail
    return await get_for_crew_user(session, user, order_id)


async def active_crew_of(session: AsyncSession, user: User) -> Crew | None:
    crew = await CrewRepository(session).get_by_app_user(user.id)
    if crew is None or not crew.is_active or crew.deleted_at is not None:
        return None
    return crew


async def _technician_orders(
    session: AsyncSession, rows: Sequence[OpenCrewOrderRow]
) -> list[OrderTechnicianOut]:
    """Arma las órdenes como las ve el técnico: la lista y el detalle no se desfasan."""
    site_ids = {site.id for _, _, _, site, _, _, _ in rows}
    contacts = await ClientContactRepository(session).list_for_sites(site_ids) if rows else []
    names_by_site: dict[uuid.UUID, list[str]] = {}
    for contact in contacts:
        if contact.name and contact.client_site_id is not None:
            names_by_site.setdefault(contact.client_site_id, []).append(contact.name)

    return [
        OrderTechnicianOut(
            id=order.id,
            number=order.number,
            status=order.status,
            work_type_name=work_type_name,
            description=order.description,
            client_name=client_name,
            scheduled_for=scheduled_for,
            site=ClientSiteTechnicianOut(
                address=site.address,
                reference=site.reference,
                map_url=site_map_url(site.address),
                contact_names=names_by_site.get(site.id, []),
            ),
            equipment=(
                EquipmentTechnicianOut(
                    location_note=equipment.location_note,
                    equipment_type_name=equipment_type_name or "",
                    brand=equipment.brand,
                    model=equipment.model,
                )
                if equipment is not None
                else None
            ),
        )
        for (
            order,
            scheduled_for,
            client_name,
            site,
            work_type_name,
            equipment,
            equipment_type_name,
        ) in rows
    ]


def _columns(order: WorkOrder) -> dict[str, object]:
    return {column.key: getattr(order, column.key) for column in WorkOrder.__table__.columns}


async def get_work_order(session: AsyncSession, order_id: uuid.UUID) -> WorkOrder:
    order = await WorkOrderRepository(session).get(order_id)
    if order is None:
        raise WorkOrderNotFoundError
    return order


async def apply_transition(
    session: AsyncSession,
    order: WorkOrder,
    action: OrderAction,
    actor: User,
    note: str | None,
) -> WorkOrderEvent:
    """Aplica una acción sobre la orden tal como se leyó y registra su evento.

    El estado y el evento van en la misma transacción. El UPDATE exige que el estado
    siga siendo el leído: si otro lo cambió antes, no toca nada y da conflicto.
    """
    event = await stage_transition(session, order, action, actor, note)
    await session.commit()
    await session.refresh(order)
    await session.refresh(event)
    return event


async def stage_transition(
    session: AsyncSession,
    order: WorkOrder,
    action: OrderAction,
    actor: User,
    note: str | None,
) -> WorkOrderEvent:
    """Cambia el estado y agrega el evento sin confirmar, para sumar más en la transacción."""
    current = order.status
    transition = resolve_transition(current, action, actor.role, note)
    repository = WorkOrderRepository(session)
    changed = await repository.update_status_if(
        order.id, expected=current, new=transition.to_status
    )
    if not changed:
        await session.rollback()
        raise OrderStatusConflictError
    event = WorkOrderEvent(
        work_order_id=order.id,
        event_type=transition.event_type,
        from_status=current,
        to_status=transition.to_status,
        actor_id=actor.id,
        note=note,
    )
    repository.add_event(event)
    return event


async def record_event(
    session: AsyncSession,
    order: WorkOrder,
    event_type: WorkOrderEventType,
    actor: User,
    note: str | None = None,
) -> WorkOrderEvent:
    """Registra un hecho de la orden que no cambia su estado (reasignación, aprobación)."""
    if event_type not in STATUSLESS_EVENT_TYPES:
        raise ValueError(f"{event_type} cambia el estado: usá apply_transition")
    event = WorkOrderEvent(
        work_order_id=order.id, event_type=event_type, actor_id=actor.id, note=note
    )
    WorkOrderRepository(session).add_event(event)
    await session.commit()
    await session.refresh(event)
    return event


async def assign_work_order(
    session: AsyncSession, order_id: uuid.UUID, data: AssignmentCreate, actor: User
) -> WorkOrderAssignment:
    """Asigna una orden Pendiente a una escuadrilla activa para un día (de hoy en adelante).

    Estado, evento y asignación van en la misma transacción.
    """
    order = await get_work_order(session, order_id)
    crew = await CrewRepository(session).get(data.crew_id)
    if crew is None or not crew.is_active:
        raise CrewNotAvailableError
    if data.scheduled_for < business_today():
        raise ScheduledDateInPastError
    if order.requires_approval:
        raise OrderRequiresApprovalError

    note = f"Escuadrilla: {crew.name}. Fecha prevista: {format_date(data.scheduled_for)}."
    await stage_transition(session, order, OrderAction.assign, actor, note)
    assignment = WorkOrderAssignment(
        work_order_id=order.id,
        crew_id=crew.id,
        scheduled_for=data.scheduled_for,
    )
    session.add(assignment)
    await session.commit()
    await session.refresh(assignment)
    return assignment
