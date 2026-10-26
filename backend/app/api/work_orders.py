from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import SessionDep, require_role
from app.api.schemas.work_order import PendingOrderPage, WorkOrderAdminOut, WorkOrderCreate
from app.db.models.user import User, UserRole
from app.services import catalog as catalog_service
from app.services import clients as clients_service
from app.services import work_orders as work_orders_service

router = APIRouter(prefix="/admin/orders", tags=["órdenes"])

# Errores de lo elegido en el pedido: cliente, domicilio o tipo de trabajo.
_CHOICE_ERROR_DETAIL: dict[type[Exception], tuple[int, str, str]] = {
    clients_service.ClientNotFoundError: (404, "client_not_found", "No se encontró el cliente."),
    clients_service.SiteNotFoundError: (404, "site_not_found", "No se encontró el domicilio."),
    clients_service.SiteOfAnotherClientError: (
        422,
        "site_of_another_client",
        "El domicilio es de otro cliente.",
    ),
    clients_service.SiteInactiveError: (422, "site_inactive", "El domicilio está desactivado."),
    catalog_service.WorkTypeNotFoundError: (
        404,
        "work_type_not_found",
        "No se encontró el tipo de trabajo.",
    ),
    work_orders_service.WorkTypeInactiveError: (
        422,
        "work_type_inactive",
        "El tipo de trabajo está desactivado.",
    ),
}
_CHOICE_ERRORS = tuple(_CHOICE_ERROR_DETAIL)

# Solo administración crea órdenes; dirección las ve en el panel (E04-05).
AdminOnly = Annotated[User, Depends(require_role(UserRole.admin))]


@router.post("", response_model=WorkOrderAdminOut, status_code=status.HTTP_201_CREATED)
async def create_work_order(
    payload: WorkOrderCreate, session: SessionDep, admin: AdminOnly
) -> WorkOrderAdminOut:
    try:
        return await work_orders_service.create_work_order(session, payload, admin)
    except _CHOICE_ERRORS as exc:
        status_code, code, message = _CHOICE_ERROR_DETAIL[type(exc)]
        raise HTTPException(
            status_code=status_code, detail={"code": code, "message": message}
        ) from None


# Por ahora solo pendientes, que es desde donde se asigna (E04-03); el panel por estado
# con filtros llega con E04-05.
@router.get("", response_model=PendingOrderPage)
async def list_work_orders(
    session: SessionDep,
    _: AdminOnly,
    status: Literal["pending"],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> PendingOrderPage:
    items, total = await work_orders_service.list_pending(session, limit=limit, offset=offset)
    return PendingOrderPage(items=items, total=total, limit=limit, offset=offset)
