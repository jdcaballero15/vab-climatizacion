import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.client import ClientSiteTechnicianOut, site_map_url
from app.api.schemas.work_order import (
    AssignmentCreate,
    CancellationAdminOut,
    CancellationCreate,
    CompletedOut,
    CrewDoneOrdersTechnicianOut,
    CrewOrdersTechnicianOut,
    CrewTechnicianOut,
    CurrentAssignmentOut,
    DoneOrderTechnicianOut,
    EquipmentTechnicianOut,
    OrderDetailTechnicianOut,
    OrderEquipmentOut,
    OrderListItemOut,
    OrderTechnicianOut,
    ReturnedFromCrewOut,
    UnassignmentCreate,
    WorkOrderAdminOut,
    WorkOrderCreate,
)
from app.core.dates import business_today, format_date
from app.db.models.crew import Crew
from app.db.models.equipment import Equipment
from app.db.models.user import User
from app.db.models.work_order import (
    WorkOrder,
    WorkOrderAssignment,
    WorkOrderCancellation,
    WorkOrderClosure,
    WorkOrderEvent,
)
from app.db.repositories.client import ClientContactRepository
from app.db.repositories.crew import CrewRepository
from app.db.repositories.equipment import EquipmentRepository
from app.db.repositories.work_order import OpenCrewOrderRow, WorkOrderRepository
from app.domain.work_order import (
    CANCEL_REASON_LABELS,
    CREW_OPEN_STATUSES,
    STATUSLESS_EVENT_TYPES,
    BillingStatus,
    CancelReason,
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


class EquipmentNotAvailableError(Exception):
    """El equipo no existe, está dado de baja o no es del domicilio de la orden (E04-12)."""


class OrderNotEditableError(Exception):
    """La orden ya se inició: su equipo no se cambia (E04-12)."""


class WorkTypeInactiveError(Exception):
    """El tipo de trabajo elegido está desactivado."""


class CrewNotAvailableError(Exception):
    """La escuadrilla elegida no existe o está desactivada."""


class ScheduledDateInPastError(Exception):
    """La fecha prevista es anterior a hoy."""


class SameAssignmentError(Exception):
    """La reasignación deja la misma escuadrilla y la misma fecha (E04-04, criterio 6)."""


class OrderRequiresApprovalError(Exception):
    """La orden es de un lote de mantenimiento sin aprobar (R6)."""


class CancellationValidationError(Exception):
    """Motivo de cancelación incompleto. Lleva el campo para la app."""

    def __init__(self, code: str, field: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.field = field
        self.message = message


async def create_work_order(
    session: AsyncSession, data: WorkOrderCreate, actor: User
) -> WorkOrderAdminOut:
    """Alta manual desde administración: queda Pendiente, con su evento de creación."""
    await clients_service.get_client(session, data.client_id)
    await clients_service.check_active_site_of_client(session, data.client_id, data.client_site_id)
    work_type = await catalog_service.get_work_type(session, data.work_type_id)
    if not work_type.is_active:
        raise WorkTypeInactiveError
    if data.equipment_id is not None:
        await _check_equipment(session, data.equipment_id, data.client_site_id)

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


# El equipo se elige o se cambia hasta que la escuadrilla inicia la orden (E04-12).
EQUIPMENT_EDITABLE_STATUSES = frozenset({OrderStatus.pending, OrderStatus.assigned})
NO_EQUIPMENT = "sin equipo"


async def _check_equipment(
    session: AsyncSession, equipment_id: uuid.UUID, site_id: uuid.UUID
) -> Equipment:
    """Un equipo vigente del domicilio de la orden (E04-12, criterio 4)."""
    equipment = await EquipmentRepository(session).get(equipment_id)
    if equipment is None or equipment.client_site_id != site_id:
        raise EquipmentNotAvailableError
    return equipment


async def change_equipment(
    session: AsyncSession, order_id: uuid.UUID, equipment_id: uuid.UUID | None, actor: User
) -> WorkOrderAdminOut:
    """Agrega, cambia o saca el equipo de una orden Pendiente o Asignada (E04-12).

    Cada cambio queda en la línea de tiempo con el código anterior y el nuevo. Elegir el
    que ya tiene no es un cambio.
    """
    repo = WorkOrderRepository(session)
    order = await get_work_order(session, order_id)
    if order.status not in EQUIPMENT_EDITABLE_STATUSES:
        raise OrderNotEditableError
    new = (
        await _check_equipment(session, equipment_id, order.client_site_id)
        if equipment_id is not None
        else None
    )
    if order.equipment_id != equipment_id:
        old = (
            await EquipmentRepository(session).get(order.equipment_id, include_deleted=True)
            if order.equipment_id is not None
            else None
        )
        # Si la escuadrilla la inició mientras tanto, ya no se cambia.
        if not await repo.update_equipment_if(
            order.id, equipment_id, statuses=EQUIPMENT_EDITABLE_STATUSES
        ):
            raise OrderNotEditableError
        repo.add_event(
            WorkOrderEvent(
                work_order_id=order.id,
                event_type=WorkOrderEventType.equipment_changed,
                actor_id=actor.id,
                note=(
                    f"Equipo: {old.internal_code if old else NO_EQUIPMENT}"
                    f" -> {new.internal_code if new else NO_EQUIPMENT}"
                ),
            )
        )
        await session.commit()
        await session.refresh(order)
    created_at = await repo.created_at(order.id)
    return WorkOrderAdminOut.model_validate({**_columns(order), "created_at": created_at})


async def list_by_status(
    session: AsyncSession,
    status: OrderStatus,
    *,
    billing: BillingStatus | None = None,
    limit: int,
    offset: int,
) -> tuple[list[OrderListItemOut], int]:
    rows, total = await WorkOrderRepository(session).list_by_status_page(
        status, billing=billing, limit=limit, offset=offset
    )
    items = [
        OrderListItemOut(
            id=order.id,
            number=order.number,
            status=order.status,
            client_id=order.client_id,
            client_name=client_name,
            client_site_id=order.client_site_id,
            site_label=site_label,
            site_address=site_address,
            work_type_name=work_type_name,
            description=order.description,
            created_at=created_at,
            returned=(
                _returned(closure, assigned_at, crew_name, crew_id)
                if status == OrderStatus.pending
                else None
            ),
            # La última asignación de una orden Asignada o En curso es la vigente.
            assignment=(
                CurrentAssignmentOut(crew_name=crew_name, scheduled_for=scheduled_for)
                if status in CREW_OPEN_STATUSES and crew_name and scheduled_for
                else None
            ),
            cancellation=(
                _cancellation_out(cancellation, cancelled_by_name)
                if cancellation is not None and cancelled_by_name is not None
                else None
            ),
            # La última asignación de una Terminada es la de la escuadrilla que la cerró.
            completed=(
                CompletedOut(crew_name=crew_name, closed_at=closure.closed_at)
                if status == OrderStatus.done and closure is not None
                else None
            ),
            equipment=(
                OrderEquipmentOut(
                    id=equipment.id,
                    internal_code=equipment.internal_code,
                    location_note=equipment.location_note,
                )
                if equipment is not None
                else None
            ),
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
            crew_id,
            scheduled_for,
            cancellation,
            cancelled_by_name,
            equipment,
        ) in rows
    ]
    return items, total


def _returned(
    closure: WorkOrderClosure | None,
    assigned_at: datetime | None,
    crew_name: str | None,
    crew_id: uuid.UUID | None,
) -> ReturnedFromCrewOut | None:
    """El último cierre explica por qué está Pendiente solo si no se la reasignó después.

    La escuadrilla es la de la última asignación, que es la que terminó ese cierre.
    """
    if closure is None or assigned_at is None or crew_name is None or crew_id is None:
        return None
    if closure.outcome == ClosureOutcome.done:
        return None
    if assigned_at > closure.closed_at:
        return None
    return ReturnedFromCrewOut(
        crew_id=crew_id,
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


# "Hechas esta semana" son los últimos 7 días, no desde el lunes (E05-14).
DONE_WINDOW = timedelta(days=7)


async def list_done_for_crew_user(session: AsyncSession, user: User) -> CrewDoneOrdersTechnicianOut:
    """Cierres de la escuadrilla del usuario en los últimos 7 días (E05-14).

    Cualquier resultado; una fila por cierre. Sin escuadrilla activa, ninguno.
    """
    crew = await active_crew_of(session, user)
    if crew is None:
        return CrewDoneOrdersTechnicianOut(crew=None, orders=[])
    since = datetime.now(UTC) - DONE_WINDOW
    rows = await WorkOrderRepository(session).list_closures_for_crew(crew.id, since=since)
    return CrewDoneOrdersTechnicianOut(
        crew=CrewTechnicianOut(name=crew.name),
        orders=[
            DoneOrderTechnicianOut(
                id=order.id,
                number=order.number,
                work_type_name=work_type_name,
                description=order.description,
                client_name=client_name,
                address=address,
                outcome=closure.outcome,
                not_done_reason=closure.not_done_reason,
                closed_at=closure.closed_at,
            )
            for closure, order, work_type_name, client_name, address in rows
        ],
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


async def cancel_work_order(
    session: AsyncSession, order_id: uuid.UUID, data: CancellationCreate, actor: User
) -> CancellationAdminOut:
    """Cancela una orden Pendiente, Asignada o En curso con su motivo (E04-07).

    Estado, evento, fin de la asignación vigente y cancelación van en una transacción.
    """
    reason = CancelReason(data.reason)
    if reason == CancelReason.other and data.reason_text is None:
        raise CancellationValidationError(
            "reason_text_required", "reason_text", 'Escribí el motivo de "Otro".'
        )
    if reason != CancelReason.other and data.reason_text is not None:
        raise CancellationValidationError(
            "reason_text_not_allowed", "reason_text", 'El texto va solo con el motivo "Otro".'
        )

    order = await get_work_order(session, order_id)
    label = CANCEL_REASON_LABELS[reason]
    note = f"{label}: {data.reason_text}" if reason == CancelReason.other else f"{label}."
    await stage_transition(session, order, OrderAction.cancel, actor, note)
    await WorkOrderRepository(session).end_current_assignment(order.id)
    cancellation = WorkOrderCancellation(
        work_order_id=order.id,
        reason=reason,
        reason_text=data.reason_text,
        cancelled_by=actor.id,
    )
    session.add(cancellation)
    await session.commit()
    await session.refresh(cancellation)
    await session.refresh(actor)
    return _cancellation_out(cancellation, actor.full_name)


def _cancellation_out(
    cancellation: WorkOrderCancellation, cancelled_by_name: str
) -> CancellationAdminOut:
    return CancellationAdminOut(
        reason=cancellation.reason,
        reason_text=cancellation.reason_text,
        cancelled_by_name=cancelled_by_name,
        cancelled_at=cancellation.cancelled_at,
    )


async def assign_work_order(
    session: AsyncSession, order_id: uuid.UUID, data: AssignmentCreate, actor: User
) -> WorkOrderAssignment:
    """Asigna una orden Pendiente a una escuadrilla activa para un día (de hoy en adelante).

    Estado, evento y asignación van en la misma transacción.
    """
    order = await get_work_order(session, order_id)
    crew = await _available_crew(session, data)
    if order.requires_approval:
        raise OrderRequiresApprovalError

    await stage_transition(session, order, OrderAction.assign, actor, _assignment_note(crew, data))
    return await _add_assignment(session, order, crew, data)


async def reassign_work_order(
    session: AsyncSession, order_id: uuid.UUID, data: AssignmentCreate, actor: User
) -> WorkOrderAssignment:
    """Pasa una orden Asignada o En curso a otra escuadrilla o fecha (E04-04, R9).

    La nueva escuadrilla la recibe Asignada. Lo ya registrado (cierres anteriores) se
    conserva. Estado, evento, fin de la asignación vigente y la nueva, en una transacción.
    """
    order = await get_work_order(session, order_id)
    crew = await _available_crew(session, data)
    current = await WorkOrderRepository(session).current_assignment(order.id)
    if (
        current is not None
        and current.crew_id == crew.id
        and current.scheduled_for == data.scheduled_for
    ):
        raise SameAssignmentError

    note = _assignment_note(crew, data)
    await stage_transition(session, order, OrderAction.reassign, actor, note)
    await WorkOrderRepository(session).end_current_assignment(order.id)
    return await _add_assignment(session, order, crew, data)


async def unassign_work_order(
    session: AsyncSession, order_id: uuid.UUID, data: UnassignmentCreate, actor: User
) -> None:
    """Devuelve una orden Asignada a Pendiente, sin escuadrilla ni fecha (E04-04)."""
    order = await get_work_order(session, order_id)
    note = f"Motivo: {data.reason}." if data.reason else None
    await stage_transition(session, order, OrderAction.unassign, actor, note)
    await WorkOrderRepository(session).end_current_assignment(order.id)
    await session.commit()


async def _available_crew(session: AsyncSession, data: AssignmentCreate) -> Crew:
    crew = await CrewRepository(session).get(data.crew_id)
    if crew is None or not crew.is_active:
        raise CrewNotAvailableError
    if data.scheduled_for < business_today():
        raise ScheduledDateInPastError
    return crew


def _assignment_note(crew: Crew, data: AssignmentCreate) -> str:
    note = f"Escuadrilla: {crew.name}. Fecha prevista: {format_date(data.scheduled_for)}."
    return f"{note} Motivo: {data.reason}." if data.reason else note


async def _add_assignment(
    session: AsyncSession, order: WorkOrder, crew: Crew, data: AssignmentCreate
) -> WorkOrderAssignment:
    assignment = WorkOrderAssignment(
        work_order_id=order.id,
        crew_id=crew.id,
        scheduled_for=data.scheduled_for,
    )
    session.add(assignment)
    try:
        await session.commit()
    except IntegrityError:
        # Otra asignación vigente apareció a la vez (índice de una sola vigente por orden).
        await session.rollback()
        raise OrderStatusConflictError from None
    await session.refresh(assignment)
    return assignment
