import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep, require_role
from app.api.schemas.work_order import InvoiceCreate, InvoiceOut, InvoiceUpdate
from app.db.models.user import User, UserRole
from app.services import billing as billing_service
from app.services import work_orders as work_orders_service

router = APIRouter(prefix="/admin/invoices", tags=["facturas"])

AdminOnly = Annotated[User, Depends(require_role(UserRole.admin))]


@router.post("", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    payload: InvoiceCreate, session: SessionDep, admin: AdminOnly
) -> InvoiceOut:
    """Registra una factura para una o varias órdenes y las pasa a Facturada (E04-09)."""
    try:
        return await billing_service.create_invoice(session, payload, admin)
    except work_orders_service.WorkOrderNotFoundError:
        raise _error(404, "order_not_found", "No se encontró alguna de las órdenes.") from None
    except billing_service.InvoiceOrdersError as exc:
        raise _error(409, exc.code, exc.message) from None
    except work_orders_service.OrderStatusConflictError as exc:
        raise _error(409, exc.code, exc.message) from None


@router.put("/{invoice_id}", response_model=InvoiceOut)
async def update_invoice(
    invoice_id: uuid.UUID, payload: InvoiceUpdate, session: SessionDep, admin: AdminOnly
) -> InvoiceOut:
    """Corrige número o fecha; queda en la línea de tiempo de cada orden (criterio 4)."""
    try:
        return await billing_service.update_invoice(session, invoice_id, payload, admin)
    except billing_service.InvoiceNotFoundError:
        raise _error(404, "invoice_not_found", "No se encontró la factura.") from None


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})
