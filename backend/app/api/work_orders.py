import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import SessionDep, require_role
from app.api.schemas.work_order import (
    AssignmentAdminOut,
    AssignmentCreate,
    CancellationAdminOut,
    CancellationCreate,
    OrderListPage,
    WorkOrderAdminOut,
    WorkOrderCreate,
)
from app.db.models.user import User, UserRole
from app.db.models.work_order import WorkOrderAssignment
from app.domain.work_order import (
    InvalidTransitionError,
    OrderStatus,
    ReasonRequiredError,
    TransitionRoleError,
    WorkOrderRuleError,
)
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

# Reglas de la máquina de estados: no se puede en el estado actual es un conflicto (409).
_RULE_STATUS: dict[type[WorkOrderRuleError], int] = {
    InvalidTransitionError: 409,
    TransitionRoleError: 403,
    ReasonRequiredError: 422,
}

_ASSIGNMENT_ERROR_DETAIL: dict[type[Exception], tuple[int, str, str]] = {
    work_orders_service.WorkOrderNotFoundError: (
        404,
        "order_not_found",
        "No se encontró la orden.",
    ),
    work_orders_service.CrewNotAvailableError: (
        422,
        "crew_not_available",
        "Elegí una escuadrilla activa.",
    ),
    work_orders_service.ScheduledDateInPastError: (
        422,
        "scheduled_date_in_past",
        "La fecha prevista no puede ser anterior a hoy.",
    ),
    work_orders_service.OrderRequiresApprovalError: (
        422,
        "order_requires_approval",
        "La orden se puede asignar recién cuando se apruebe su lote de mantenimiento.",
    ),
    work_orders_service.OrderStatusConflictError: (
        409,
        work_orders_service.OrderStatusConflictError.code,
        work_orders_service.OrderStatusConflictError.message,
    ),
}
_ASSIGNMENT_ERRORS = tuple(_ASSIGNMENT_ERROR_DETAIL)

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
        raise _error(status_code, code, message) from None


# Los estados desde los que se asigna (E04-03) o se cancela (E04-07), y las canceladas;
# el panel completo con filtros llega con E04-05.
ListableStatus = Literal["pending", "assigned", "in_progress", "cancelled"]


@router.get("", response_model=OrderListPage)
async def list_work_orders(
    session: SessionDep,
    _: AdminOnly,
    status: ListableStatus,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OrderListPage:
    items, total = await work_orders_service.list_by_status(
        session, OrderStatus(status), limit=limit, offset=offset
    )
    return OrderListPage(items=items, total=total, limit=limit, offset=offset)


@router.post(
    "/{order_id}/assignment",
    response_model=AssignmentAdminOut,
    status_code=status.HTTP_201_CREATED,
)
async def assign_work_order(
    order_id: uuid.UUID, payload: AssignmentCreate, session: SessionDep, admin: AdminOnly
) -> WorkOrderAssignment:
    try:
        return await work_orders_service.assign_work_order(session, order_id, payload, admin)
    except _ASSIGNMENT_ERRORS as exc:
        status_code, code, message = _ASSIGNMENT_ERROR_DETAIL[type(exc)]
        raise _error(status_code, code, message) from None
    except WorkOrderRuleError as exc:
        raise _error(_RULE_STATUS[type(exc)], exc.code, exc.message) from None


@router.post(
    "/{order_id}/cancellation",
    response_model=CancellationAdminOut,
    status_code=status.HTTP_201_CREATED,
)
async def cancel_work_order(
    order_id: uuid.UUID, payload: CancellationCreate, session: SessionDep, admin: AdminOnly
) -> CancellationAdminOut:
    try:
        return await work_orders_service.cancel_work_order(session, order_id, payload, admin)
    except work_orders_service.CancellationValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": exc.code, "message": exc.message, "field": exc.field},
        ) from None
    except (
        work_orders_service.WorkOrderNotFoundError,
        work_orders_service.OrderStatusConflictError,
    ) as exc:
        status_code, code, message = _ASSIGNMENT_ERROR_DETAIL[type(exc)]
        raise _error(status_code, code, message) from None
    except WorkOrderRuleError as exc:
        raise _error(_RULE_STATUS[type(exc)], exc.code, exc.message) from None


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})
