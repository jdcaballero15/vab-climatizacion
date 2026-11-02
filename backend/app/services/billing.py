"""Importes y estado de cobro de una orden terminada (E04-14, versión mínima).

Provisorio hasta definir con la oficina la factura, el cobro y la mano de obra (E04-09 a
E04-11): no cambia el estado de la orden, que sigue Terminada. Los repuestos son el total
de materiales de la orden (E05-05); la columna parts_amount guarda el último calculado.
"""

import uuid
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.work_order import BillingAdminOut, BillingUpdate
from app.db.models.user import User
from app.db.models.work_order import WorkOrderBilling
from app.domain.work_order import BillingStatus, OrderStatus
from app.services import order_materials
from app.services.work_orders import get_work_order


class OrderNotDoneError(Exception):
    code = "order_not_done"
    message = "Solo se cargan importes en una orden terminada."


class OrderNotApprovedError(Exception):
    code = "order_not_approved"
    message = "Aprobá la orden antes de marcarla facturada."


async def save_billing(
    session: AsyncSession, order_id: uuid.UUID, data: BillingUpdate, actor: User
) -> BillingAdminOut:
    """Guarda o reemplaza los importes y el estado de cobro de la orden."""
    order = await get_work_order(session, order_id)
    if order.status != OrderStatus.done:
        raise OrderNotDoneError
    if data.status == BillingStatus.invoiced and not await order_materials.is_approved(
        session, order.id
    ):
        raise OrderNotApprovedError
    # Antes de crear la fila: la consulta del total haría flush de una fila sin importes.
    parts_amount = await order_materials.materials_total(session, order.id)
    billing = await _current(session, order.id)
    if billing is None:
        billing = WorkOrderBilling(work_order_id=order.id)
        session.add(billing)
    billing.parts_amount = parts_amount
    billing.labor_amount = data.labor_amount
    billing.status = data.status
    billing.invoice_number = data.invoice_number
    billing.updated_by = actor.id
    await session.commit()
    await session.refresh(billing)
    return _out(billing, actor.full_name)


async def billing_by_order(
    session: AsyncSession, order_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, BillingAdminOut]:
    """Los cobros cargados de esas órdenes, para el listado de terminadas."""
    if not order_ids:
        return {}
    result = await session.execute(
        select(WorkOrderBilling, User.full_name)
        .join(User, User.id == WorkOrderBilling.updated_by)
        .where(
            WorkOrderBilling.work_order_id.in_(order_ids),
            WorkOrderBilling.deleted_at.is_(None),
        )
    )
    out: dict[uuid.UUID, BillingAdminOut] = {}
    for billing, name in result.all():
        # Hasta aprobar, el total de materiales sigue la lista: se recalcula al listar.
        parts = await order_materials.materials_total(session, billing.work_order_id)
        out[billing.work_order_id] = _out(billing, name, parts)
    return out


async def _current(session: AsyncSession, order_id: uuid.UUID) -> WorkOrderBilling | None:
    return await session.scalar(
        select(WorkOrderBilling).where(
            WorkOrderBilling.work_order_id == order_id, WorkOrderBilling.deleted_at.is_(None)
        )
    )


def _out(
    billing: WorkOrderBilling, updated_by_name: str, parts_amount: Decimal | None = None
) -> BillingAdminOut:
    parts = billing.parts_amount if parts_amount is None else parts_amount
    return BillingAdminOut(
        parts_amount=parts,
        labor_amount=billing.labor_amount,
        total=parts + billing.labor_amount,
        status=billing.status,
        invoice_number=billing.invoice_number,
        updated_by_name=updated_by_name,
        updated_at=billing.updated_at,
    )
