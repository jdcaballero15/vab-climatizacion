import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.work_order import (
    AssignmentCreate,
    PendingOrderOut,
    WorkOrderAdminOut,
    WorkOrderCreate,
)
from app.core.dates import business_today, format_date
from app.db.models.user import User, UserRole
from app.db.models.work_order import WorkOrder, WorkOrderAssignment, WorkOrderEvent
from app.db.repositories.user import UserRepository
from app.db.repositories.work_order import WorkOrderRepository
from app.domain.work_order import (
    STATUSLESS_EVENT_TYPES,
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


class TechnicianNotAvailableError(Exception):
    """El usuario elegido no existe, está inactivo o no es técnico."""


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
        )
        for order, created_at, client_name, site_label, site_address, work_type_name in rows
    ]
    return items, total


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
    event = await _stage_transition(session, order, action, actor, note)
    await session.commit()
    await session.refresh(order)
    await session.refresh(event)
    return event


async def _stage_transition(
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
    """Asigna una orden Pendiente a un técnico activo para un día (de hoy en adelante).

    Estado, evento y asignación van en la misma transacción.
    """
    order = await get_work_order(session, order_id)
    technician = await UserRepository(session).get(data.technician_id)
    if technician is None or not technician.is_active or technician.role != UserRole.technician:
        raise TechnicianNotAvailableError
    if data.scheduled_for < business_today():
        raise ScheduledDateInPastError
    if order.requires_approval:
        raise OrderRequiresApprovalError

    note = f"Técnico: {technician.full_name}. Fecha prevista: {format_date(data.scheduled_for)}."
    await _stage_transition(session, order, OrderAction.assign, actor, note)
    assignment = WorkOrderAssignment(
        work_order_id=order.id,
        technician_id=technician.id,
        scheduled_for=data.scheduled_for,
    )
    session.add(assignment)
    await session.commit()
    await session.refresh(assignment)
    return assignment
