"""Materiales de una orden en administración: total, correcciones y aprobación (E05-05, E04-08).

Mientras la orden no está aprobada, cada línea toma el precio vigente de la lista. Al
aprobarla se estampa ese precio en part_usage.unit_price y ya no cambia (ADR 0005).
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.order_materials import (
    MaterialLineAdminOut,
    MaterialLineCreate,
    MaterialLinePromotion,
    MaterialLineUpdate,
    OrderMaterialsAdminOut,
)
from app.db.models.part import Part, PartUsage
from app.db.models.user import User
from app.db.models.work_order import WorkOrder, WorkOrderClosure, WorkOrderEvent
from app.db.repositories.part import PartRepository
from app.db.repositories.work_order import WorkOrderRepository
from app.domain.work_order import OrderStatus, WorkOrderEventType
from app.services import parts as parts_service
from app.services.work_orders import get_work_order


class OrderApprovedError(Exception):
    code = "order_already_approved"
    message = "La orden ya está aprobada: sus materiales y precios no cambian."


class OrderNotEditableError(Exception):
    code = "order_not_editable"
    message = "Los materiales de esta orden ya no se pueden cambiar."


class OrderNotDoneError(Exception):
    code = "order_not_done"
    message = "Solo se aprueba una orden terminada."


class OtherMaterialsPendingError(Exception):
    code = "other_materials_pending"
    message = 'Pasá a la lista o sacá los materiales "Otro" antes de aprobar.'


class LineNotOtherError(Exception):
    code = "line_not_other"
    message = 'Solo se pasa a la lista un material cargado como "Otro".'


class MaterialLineNotFoundError(Exception):
    """No existe esa línea de materiales en la orden."""


class MaterialLineInvalidError(Exception):
    """Línea sin material ni texto, con los dos, o con un material que no está activo."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


# Estados en que ya no se tocan los materiales, aunque no haya aprobación registrada.
_CLOSED = {OrderStatus.cancelled, OrderStatus.invoiced, OrderStatus.paid}


async def get_materials(session: AsyncSession, order_id: uuid.UUID) -> OrderMaterialsAdminOut:
    order = await get_work_order(session, order_id)
    return await _materials(session, order)


async def materials_total(session: AsyncSession, order_id: uuid.UUID) -> Decimal:
    order = await get_work_order(session, order_id)
    return (await _materials(session, order)).total


async def is_approved(session: AsyncSession, order_id: uuid.UUID) -> bool:
    return await _approval(session, order_id) is not None


async def add_line(
    session: AsyncSession, order_id: uuid.UUID, data: MaterialLineCreate, actor: User
) -> OrderMaterialsAdminOut:
    order = await _editable(session, order_id)
    part = await _line_part(session, data)
    session.add(
        PartUsage(
            work_order_id=order.id,
            part_id=part.id if part else None,
            other_text=data.other_text,
            quantity=data.quantity,
            created_by=actor.id,
        )
    )
    name = part.name if part else data.other_text
    note = f"Agregado: {name}, {_qty(data.quantity)} {part.unit if part else ''}".rstrip()
    return await _commit_change(session, order, actor, note)


async def update_line(
    session: AsyncSession,
    order_id: uuid.UUID,
    line_id: uuid.UUID,
    data: MaterialLineUpdate,
    actor: User,
) -> OrderMaterialsAdminOut:
    order = await _editable(session, order_id)
    line = await _line(session, order, line_id)
    name, unit = await _label(session, line)
    note = f"{name}: {_qty(line.quantity)} -> {_qty(data.quantity)} {unit}".rstrip()
    line.quantity = data.quantity
    return await _commit_change(session, order, actor, note)


async def remove_line(
    session: AsyncSession, order_id: uuid.UUID, line_id: uuid.UUID, actor: User
) -> OrderMaterialsAdminOut:
    order = await _editable(session, order_id)
    line = await _line(session, order, line_id)
    name, unit = await _label(session, line)
    line.deleted_at = datetime.now(UTC)
    note = f"Sacado: {name}, {_qty(line.quantity)} {unit}".rstrip()
    return await _commit_change(session, order, actor, note)


async def promote_line(
    session: AsyncSession,
    order_id: uuid.UUID,
    line_id: uuid.UUID,
    data: MaterialLinePromotion,
    actor: User,
) -> OrderMaterialsAdminOut:
    """La línea "Otro" pasa a ser el material de la lista, con su precio (E02-07)."""
    order = await _editable(session, order_id)
    line = await _line(session, order, line_id)
    if line.part_id is not None:
        raise LineNotOtherError
    part = await _active_part(session, data.part_id)
    note = f'"{line.other_text}" pasó a la lista como {part.name}'
    line.part_id = part.id
    line.other_text = None
    return await _commit_change(session, order, actor, note)


async def approve(
    session: AsyncSession, order_id: uuid.UUID, actor: User
) -> OrderMaterialsAdminOut:
    """Aprueba la orden terminada y estampa el precio vigente en cada material (E04-08)."""
    order = await get_work_order(session, order_id)
    if await _approval(session, order.id) is not None:
        raise OrderApprovedError
    if order.status != OrderStatus.done:
        raise OrderNotDoneError
    lines = await _active_lines(session, order.id)
    if any(line.part_id is None for line in lines):
        raise OtherMaterialsPendingError
    prices = await parts_service.current_price_map(
        session, [line.part_id for line in lines if line.part_id is not None]
    )
    for line in lines:
        if line.part_id is not None:
            line.unit_price = prices.get(line.part_id, Decimal("0"))
    WorkOrderRepository(session).add_event(
        WorkOrderEvent(
            work_order_id=order.id,
            event_type=WorkOrderEventType.review_approved,
            actor_id=actor.id,
            note="Aprobada.",
        )
    )
    await session.commit()
    return await _materials(session, order)


async def _materials(session: AsyncSession, order: WorkOrder) -> OrderMaterialsAdminOut:
    approval = await _approval(session, order.id)
    rows = (
        await session.execute(
            select(PartUsage, Part, WorkOrderClosure.closed_at, User.full_name)
            .outerjoin(Part, Part.id == PartUsage.part_id)
            .outerjoin(WorkOrderClosure, WorkOrderClosure.id == PartUsage.closure_id)
            .join(User, User.id == PartUsage.created_by)
            .where(PartUsage.work_order_id == order.id, PartUsage.deleted_at.is_(None))
            .order_by(PartUsage.created_at, PartUsage.id)
        )
    ).all()
    prices = await parts_service.current_price_map(
        session, [usage.part_id for usage, *_ in rows if usage.part_id is not None]
    )
    lines: list[MaterialLineAdminOut] = []
    for usage, part, closed_at, added_by in rows:
        unit_price: Decimal | None = None
        if usage.part_id is not None:
            stamped = usage.unit_price if approval is not None else None
            unit_price = stamped if stamped is not None else prices.get(usage.part_id)
        subtotal = (
            (unit_price * usage.quantity).quantize(Decimal("0.01"))
            if unit_price is not None
            else None
        )
        lines.append(
            MaterialLineAdminOut(
                id=usage.id,
                part_id=usage.part_id,
                name=part.name if part else (usage.other_text or ""),
                unit=part.unit if part else None,
                is_other=part is None,
                quantity=usage.quantity,
                unit_price=unit_price,
                subtotal=subtotal,
                visit_closed_at=closed_at,
                added_by_name=added_by,
            )
        )
    total = sum((line.subtotal for line in lines if line.subtotal is not None), Decimal("0"))
    return OrderMaterialsAdminOut(
        approved=approval is not None,
        approved_at=approval.occurred_at if approval else None,
        lines=lines,
        total=total.quantize(Decimal("0.01")),
    )


async def _approval(session: AsyncSession, order_id: uuid.UUID) -> WorkOrderEvent | None:
    return await session.scalar(
        select(WorkOrderEvent)
        .where(
            WorkOrderEvent.work_order_id == order_id,
            WorkOrderEvent.event_type == WorkOrderEventType.review_approved,
            WorkOrderEvent.deleted_at.is_(None),
        )
        .order_by(WorkOrderEvent.occurred_at.desc())
        .limit(1)
    )


async def _editable(session: AsyncSession, order_id: uuid.UUID) -> WorkOrder:
    order = await get_work_order(session, order_id)
    if await _approval(session, order.id) is not None:
        raise OrderApprovedError
    if order.status in _CLOSED:
        raise OrderNotEditableError
    return order


async def _active_lines(session: AsyncSession, order_id: uuid.UUID) -> list[PartUsage]:
    result = await session.scalars(
        select(PartUsage).where(PartUsage.work_order_id == order_id, PartUsage.deleted_at.is_(None))
    )
    return list(result.all())


async def _line(session: AsyncSession, order: WorkOrder, line_id: uuid.UUID) -> PartUsage:
    line = await session.get(PartUsage, line_id)
    if line is None or line.work_order_id != order.id or line.deleted_at is not None:
        raise MaterialLineNotFoundError
    return line


async def _line_part(session: AsyncSession, data: MaterialLineCreate) -> Part | None:
    if data.part_id is not None and data.other_text is not None:
        raise MaterialLineInvalidError(
            "part_ambiguous", 'Elegí un material de la lista u "Otro", no las dos.'
        )
    if data.part_id is None and data.other_text is None:
        raise MaterialLineInvalidError("part_required", "Elegí un material o escribí cuál es.")
    return await _active_part(session, data.part_id) if data.part_id is not None else None


async def _active_part(session: AsyncSession, part_id: uuid.UUID) -> Part:
    part = await PartRepository(session).get(part_id)
    if part is None or not part.is_active:
        raise MaterialLineInvalidError(
            "part_not_available", "Ese material no está en la lista (o está desactivado)."
        )
    return part


async def _label(session: AsyncSession, line: PartUsage) -> tuple[str, str]:
    if line.part_id is None:
        return line.other_text or "", ""
    part = await session.get(Part, line.part_id)
    return (part.name, part.unit) if part else ("", "")


async def _commit_change(
    session: AsyncSession, order: WorkOrder, actor: User, note: str
) -> OrderMaterialsAdminOut:
    WorkOrderRepository(session).add_event(
        WorkOrderEvent(
            work_order_id=order.id,
            event_type=WorkOrderEventType.materials_changed,
            actor_id=actor.id,
            note=note,
        )
    )
    await session.commit()
    return await _materials(session, order)


def _qty(quantity: Decimal) -> str:
    """Cantidad como la escribe la oficina: 1,5 y no 1.500."""
    return f"{quantity.normalize():f}".replace(".", ",")
