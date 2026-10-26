import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.db.models.work_order import WorkOrder, WorkOrderEvent
from app.db.repositories.work_order import WorkOrderRepository
from app.domain.work_order import (
    STATUSLESS_EVENT_TYPES,
    OrderAction,
    WorkOrderEventType,
    resolve_transition,
)


class WorkOrderNotFoundError(Exception):
    """No existe una orden activa con ese id."""


class OrderStatusConflictError(Exception):
    """Otro usuario cambió el estado de la orden después de leerla."""

    code = "order_status_conflict"
    message = "La orden cambió mientras la mirabas. Volvé a cargarla e intentá de nuevo."


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
    await session.commit()
    await session.refresh(order)
    await session.refresh(event)
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
