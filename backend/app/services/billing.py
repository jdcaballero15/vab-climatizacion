"""Importes, factura y cobro de una orden cerrada (E04-09, E04-10, E04-11 y E04-14).

La mano de obra se carga a mano y los otros cargos van con descripción e importe; los
repuestos son el total de materiales de la orden (E05-05). Una factura cubre una o varias
órdenes terminadas y aprobadas y las pasa a Facturada; el cobro, con fecha y medio, a
Cobrada. Decisiones de Gonza del 2026-11-10.
"""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.work_order import (
    BillingAdminOut,
    BillingUpdate,
    ChargeAdminOut,
    ChargeWrite,
    InvoiceCreate,
    InvoiceOut,
    InvoiceUpdate,
    PaymentCreate,
    PaymentOut,
    PaymentVoid,
)
from app.db.models.user import User
from app.db.models.work_order import (
    Invoice,
    WorkOrder,
    WorkOrderBilling,
    WorkOrderCharge,
    WorkOrderInvoice,
    WorkOrderPayment,
)
from app.domain.work_order import (
    PAYMENT_METHOD_LABELS,
    OrderAction,
    OrderStatus,
    WorkOrderEventType,
)
from app.services import order_materials
from app.services.work_orders import (
    WorkOrderNotFoundError,
    get_work_order,
    record_event,
    stage_transition,
)

CENTS = Decimal("0.01")

# Las que ya cerró la escuadrilla: tienen importes.
CLOSED_STATUSES = frozenset({OrderStatus.done, OrderStatus.invoiced, OrderStatus.paid})


class OrderNotDoneError(Exception):
    code = "order_not_done"
    message = "Los importes se cargan con la orden terminada, antes de facturarla."


class OrderNotApprovedError(Exception):
    code = "order_not_approved"
    message = "Aprobá la orden antes de facturarla."


class InvoiceOrdersError(Exception):
    """Alguna orden de la factura no se puede facturar: se rechaza la factura entera."""

    code = "orders_not_invoiceable"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvoiceNotFoundError(Exception):
    pass


class ChargeNotFoundError(Exception):
    pass


class OrderNotInvoicedError(Exception):
    code = "order_not_invoiced"
    message = "Solo se registra el cobro de una orden facturada."


class OrderNotPaidError(Exception):
    code = "order_not_paid"
    message = "La orden no tiene un cobro para anular."


def _money(amount: Decimal) -> str:
    return f"$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# --- Mano de obra y otros cargos (E04-14, E04-11) ---


async def save_billing(
    session: AsyncSession, order_id: uuid.UUID, data: BillingUpdate, actor: User
) -> BillingAdminOut:
    """Guarda o reemplaza la mano de obra de la orden terminada."""
    order = await _editable(session, order_id)
    # Antes de crear la fila: la consulta del total haría flush de una fila sin importes.
    parts_amount = await order_materials.materials_total(session, order.id)
    billing = await _current(session, order.id)
    if billing is None:
        billing = WorkOrderBilling(work_order_id=order.id)
        session.add(billing)
    billing.parts_amount = parts_amount
    billing.labor_amount = data.labor_amount
    billing.updated_by = actor.id
    await session.commit()
    return await get_billing(session, order.id)


async def list_charges(session: AsyncSession, order_id: uuid.UUID) -> list[ChargeAdminOut]:
    order = await get_work_order(session, order_id)
    result = await session.execute(
        select(WorkOrderCharge, User.full_name)
        .join(User, User.id == WorkOrderCharge.created_by)
        .where(WorkOrderCharge.work_order_id == order.id, WorkOrderCharge.deleted_at.is_(None))
        .order_by(WorkOrderCharge.created_at)
    )
    return [_charge_out(charge, name) for charge, name in result.all()]


async def add_charge(
    session: AsyncSession, order_id: uuid.UUID, data: ChargeWrite, actor: User
) -> list[ChargeAdminOut]:
    order = await _editable(session, order_id)
    session.add(
        WorkOrderCharge(
            work_order_id=order.id,
            description=data.description,
            amount=data.amount,
            created_by=actor.id,
        )
    )
    note = f"Cargo agregado: {data.description}, {_money(data.amount)}"
    await record_event(session, order, WorkOrderEventType.charges_changed, actor, note)
    await session.commit()
    return await list_charges(session, order.id)


async def update_charge(
    session: AsyncSession,
    order_id: uuid.UUID,
    charge_id: uuid.UUID,
    data: ChargeWrite,
    actor: User,
) -> list[ChargeAdminOut]:
    order = await _editable(session, order_id)
    charge = await _charge(session, order.id, charge_id)
    note = (
        f"Cargo corregido: {charge.description}, {_money(charge.amount)} "
        f"pasó a {data.description}, {_money(data.amount)}"
    )
    charge.description = data.description
    charge.amount = data.amount
    await record_event(session, order, WorkOrderEventType.charges_changed, actor, note)
    await session.commit()
    return await list_charges(session, order.id)


async def remove_charge(
    session: AsyncSession, order_id: uuid.UUID, charge_id: uuid.UUID, actor: User
) -> list[ChargeAdminOut]:
    order = await _editable(session, order_id)
    charge = await _charge(session, order.id, charge_id)
    charge.deleted_at = datetime.now(UTC)
    note = f"Cargo sacado: {charge.description}, {_money(charge.amount)}"
    await record_event(session, order, WorkOrderEventType.charges_changed, actor, note)
    await session.commit()
    return await list_charges(session, order.id)


# --- Factura (E04-09) ---


async def create_invoice(session: AsyncSession, data: InvoiceCreate, actor: User) -> InvoiceOut:
    """Factura las órdenes juntas: si alguna no se puede, no se factura ninguna."""
    order_ids = list(dict.fromkeys(data.order_ids))
    orders = (
        await session.scalars(
            select(WorkOrder)
            .where(WorkOrder.id.in_(order_ids), WorkOrder.deleted_at.is_(None))
            .order_by(WorkOrder.number)
            .with_for_update()
        )
    ).all()
    if len(orders) != len(order_ids):
        raise WorkOrderNotFoundError
    not_done = [o.number for o in orders if o.status != OrderStatus.done]
    if not_done:
        raise InvoiceOrdersError(
            f"Solo se facturan órdenes terminadas. No lo están: {_numbers(not_done)}."
        )
    not_approved = [
        o.number for o in orders if not await order_materials.is_approved(session, o.id)
    ]
    if not_approved:
        raise InvoiceOrdersError(
            f"Aprobá las órdenes antes de facturarlas. Falta aprobar: {_numbers(not_approved)}."
        )
    invoice = Invoice(number=data.number, issued_on=data.issued_on, created_by=actor.id)
    session.add(invoice)
    await session.flush()
    note = f"Factura {data.number} del {data.issued_on:%d/%m/%Y}"
    for order in orders:
        session.add(WorkOrderInvoice(work_order_id=order.id, invoice_id=invoice.id))
        await stage_transition(session, order, OrderAction.invoice, actor, note)
    await session.commit()
    return await _invoice_out(session, invoice)


async def update_invoice(
    session: AsyncSession, invoice_id: uuid.UUID, data: InvoiceUpdate, actor: User
) -> InvoiceOut:
    invoice = await session.scalar(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.deleted_at.is_(None))
    )
    if invoice is None:
        raise InvoiceNotFoundError
    note = (
        f"Factura corregida: {invoice.number} del {invoice.issued_on:%d/%m/%Y} pasó a "
        f"{data.number} del {data.issued_on:%d/%m/%Y}"
    )
    invoice.number = data.number
    invoice.issued_on = data.issued_on
    for order in await _invoice_orders(session, invoice.id):
        await record_event(session, order, WorkOrderEventType.invoice_corrected, actor, note)
    await session.commit()
    return await _invoice_out(session, invoice)


# --- Cobro (E04-10) ---


async def register_payment(
    session: AsyncSession, order_id: uuid.UUID, data: PaymentCreate, actor: User
) -> BillingAdminOut:
    order = await _locked(session, order_id)
    if order.status != OrderStatus.invoiced:
        raise OrderNotInvoicedError
    session.add(
        WorkOrderPayment(
            work_order_id=order.id, paid_on=data.paid_on, method=data.method, created_by=actor.id
        )
    )
    note = f"Cobrada el {data.paid_on:%d/%m/%Y} ({PAYMENT_METHOD_LABELS[data.method]})"
    await stage_transition(session, order, OrderAction.collect, actor, note)
    await session.commit()
    return await get_billing(session, order.id)


async def void_payment(
    session: AsyncSession, order_id: uuid.UUID, data: PaymentVoid, actor: User
) -> BillingAdminOut:
    order = await _locked(session, order_id)
    payment = await _payment(session, order.id)
    if order.status != OrderStatus.paid or payment is None:
        raise OrderNotPaidError
    payment.voided_at = datetime.now(UTC)
    payment.voided_by = actor.id
    payment.void_reason = data.reason
    await stage_transition(
        session, order, OrderAction.void_payment, actor, f"Cobro anulado. Motivo: {data.reason}"
    )
    await session.commit()
    return await get_billing(session, order.id)


# --- Lectura ---


async def get_billing(session: AsyncSession, order_id: uuid.UUID) -> BillingAdminOut:
    order = await get_work_order(session, order_id)
    return (await billing_by_order(session, [order.id]))[order.id]


async def billing_by_order(
    session: AsyncSession, order_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, BillingAdminOut]:
    """Importes, factura y cobro de esas órdenes, para el listado de cerradas."""
    if not order_ids:
        return {}
    labor = {
        billing.work_order_id: (billing, name)
        for billing, name in (
            await session.execute(
                select(WorkOrderBilling, User.full_name)
                .join(User, User.id == WorkOrderBilling.updated_by)
                .where(
                    WorkOrderBilling.work_order_id.in_(order_ids),
                    WorkOrderBilling.deleted_at.is_(None),
                )
            )
        ).all()
    }
    charges = dict(
        (
            await session.execute(
                select(WorkOrderCharge.work_order_id, func.sum(WorkOrderCharge.amount))
                .where(
                    WorkOrderCharge.work_order_id.in_(order_ids),
                    WorkOrderCharge.deleted_at.is_(None),
                )
                .group_by(WorkOrderCharge.work_order_id)
            )
        ).all()
    )
    invoices = await _invoices_by_order(session, order_ids)
    payments = {
        payment.work_order_id: PaymentOut(
            paid_on=payment.paid_on,
            method=payment.method,
            created_by_name=name,
            created_at=payment.created_at,
        )
        for payment, name in (
            await session.execute(
                select(WorkOrderPayment, User.full_name)
                .join(User, User.id == WorkOrderPayment.created_by)
                .where(
                    WorkOrderPayment.work_order_id.in_(order_ids),
                    WorkOrderPayment.voided_at.is_(None),
                    WorkOrderPayment.deleted_at.is_(None),
                )
            )
        ).all()
    }
    out: dict[uuid.UUID, BillingAdminOut] = {}
    for order_id in order_ids:
        # Hasta aprobar, el total de materiales sigue la lista: se recalcula al listar.
        parts = await order_materials.materials_total(session, order_id)
        billing, name = labor.get(order_id, (None, None))
        labor_amount = (
            billing.labor_amount.quantize(CENTS) if billing is not None else Decimal("0.00")
        )
        charges_amount = (charges.get(order_id) or Decimal("0")).quantize(CENTS)
        out[order_id] = BillingAdminOut(
            parts_amount=parts,
            labor_amount=labor_amount,
            charges_amount=charges_amount,
            total=parts + labor_amount + charges_amount,
            updated_by_name=name,
            updated_at=billing.updated_at if billing is not None else None,
            invoice=invoices.get(order_id),
            payment=payments.get(order_id),
        )
    return out


async def _invoices_by_order(
    session: AsyncSession, order_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, InvoiceOut]:
    rows = (
        await session.execute(
            select(WorkOrderInvoice.work_order_id, Invoice)
            .join(Invoice, Invoice.id == WorkOrderInvoice.invoice_id)
            .where(
                WorkOrderInvoice.work_order_id.in_(order_ids),
                WorkOrderInvoice.deleted_at.is_(None),
            )
        )
    ).all()
    cache: dict[uuid.UUID, InvoiceOut] = {}
    out: dict[uuid.UUID, InvoiceOut] = {}
    for order_id, invoice in rows:
        if invoice.id not in cache:
            cache[invoice.id] = await _invoice_out(session, invoice)
        out[order_id] = cache[invoice.id]
    return out


async def _invoice_out(session: AsyncSession, invoice: Invoice) -> InvoiceOut:
    creator = await session.get(User, invoice.created_by)
    numbers = (
        await session.scalars(
            select(WorkOrder.number)
            .join(WorkOrderInvoice, WorkOrderInvoice.work_order_id == WorkOrder.id)
            .where(WorkOrderInvoice.invoice_id == invoice.id, WorkOrderInvoice.deleted_at.is_(None))
            .order_by(WorkOrder.number)
        )
    ).all()
    return InvoiceOut(
        id=invoice.id,
        number=invoice.number,
        issued_on=invoice.issued_on,
        created_by_name=creator.full_name if creator is not None else "",
        order_numbers=list(numbers),
    )


async def _invoice_orders(session: AsyncSession, invoice_id: uuid.UUID) -> Sequence[WorkOrder]:
    return (
        await session.scalars(
            select(WorkOrder)
            .join(WorkOrderInvoice, WorkOrderInvoice.work_order_id == WorkOrder.id)
            .where(WorkOrderInvoice.invoice_id == invoice_id, WorkOrderInvoice.deleted_at.is_(None))
        )
    ).all()


async def _editable(session: AsyncSession, order_id: uuid.UUID) -> WorkOrder:
    """Los importes se tocan con la orden Terminada: facturada, ya no."""
    order = await get_work_order(session, order_id)
    if order.status != OrderStatus.done:
        raise OrderNotDoneError
    return order


async def _locked(session: AsyncSession, order_id: uuid.UUID) -> WorkOrder:
    order = await session.scalar(
        select(WorkOrder)
        .where(WorkOrder.id == order_id, WorkOrder.deleted_at.is_(None))
        .with_for_update()
    )
    if order is None:
        raise WorkOrderNotFoundError
    return order


async def _current(session: AsyncSession, order_id: uuid.UUID) -> WorkOrderBilling | None:
    return await session.scalar(
        select(WorkOrderBilling).where(
            WorkOrderBilling.work_order_id == order_id, WorkOrderBilling.deleted_at.is_(None)
        )
    )


async def _charge(
    session: AsyncSession, order_id: uuid.UUID, charge_id: uuid.UUID
) -> WorkOrderCharge:
    charge = await session.scalar(
        select(WorkOrderCharge).where(
            WorkOrderCharge.id == charge_id,
            WorkOrderCharge.work_order_id == order_id,
            WorkOrderCharge.deleted_at.is_(None),
        )
    )
    if charge is None:
        raise ChargeNotFoundError
    return charge


async def _payment(session: AsyncSession, order_id: uuid.UUID) -> WorkOrderPayment | None:
    return await session.scalar(
        select(WorkOrderPayment).where(
            WorkOrderPayment.work_order_id == order_id,
            WorkOrderPayment.voided_at.is_(None),
            WorkOrderPayment.deleted_at.is_(None),
        )
    )


def _charge_out(charge: WorkOrderCharge, created_by_name: str) -> ChargeAdminOut:
    return ChargeAdminOut(
        id=charge.id,
        description=charge.description,
        amount=charge.amount.quantize(CENTS),
        created_by_name=created_by_name,
        created_at=charge.created_at,
    )


def _numbers(numbers: Sequence[int]) -> str:
    return ", ".join(f"N° {n}" for n in numbers)
