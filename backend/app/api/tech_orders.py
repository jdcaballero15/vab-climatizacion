import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import SessionDep, require_role
from app.api.schemas.closure import ClosureCreate, ClosureOptionsTechnicianOut, ClosureTechnicianOut
from app.api.schemas.work_order import CrewOrdersTechnicianOut, OrderDetailTechnicianOut
from app.db.models.user import User, UserRole
from app.services import closures as closures_service
from app.services import work_orders as work_orders_service

router = APIRouter(prefix="/tech/orders", tags=["app del técnico"])

# El usuario de la app es el de la escuadrilla (D-013).
CrewUser = Annotated[User, Depends(require_role(UserRole.technician))]


@router.get("", response_model=CrewOrdersTechnicianOut)
async def list_my_orders(session: SessionDep, user: CrewUser) -> CrewOrdersTechnicianOut:
    return await work_orders_service.list_for_crew_user(session, user)


@router.get("/{order_id}", response_model=OrderDetailTechnicianOut)
async def get_my_order(
    order_id: uuid.UUID, session: SessionDep, user: CrewUser
) -> OrderDetailTechnicianOut:
    try:
        return await work_orders_service.get_for_crew_user(session, user, order_id)
    except work_orders_service.WorkOrderNotFoundError:
        raise _order_not_found() from None


@router.post("/{order_id}/start", response_model=OrderDetailTechnicianOut)
async def start_my_order(
    order_id: uuid.UUID, session: SessionDep, user: CrewUser
) -> OrderDetailTechnicianOut:
    try:
        return await work_orders_service.start_for_crew_user(session, user, order_id)
    except work_orders_service.WorkOrderNotFoundError:
        raise _order_not_found() from None
    except work_orders_service.OrderStatusConflictError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": work_orders_service.OrderStatusConflictError.code,
                "message": work_orders_service.OrderStatusConflictError.message,
            },
        ) from None


@router.get("/{order_id}/closure-options", response_model=ClosureOptionsTechnicianOut)
async def get_closure_options(
    order_id: uuid.UUID, session: SessionDep, user: CrewUser
) -> ClosureOptionsTechnicianOut:
    try:
        return await closures_service.get_closure_options(session, user, order_id)
    except work_orders_service.WorkOrderNotFoundError:
        raise _order_not_found() from None


# 201 al cerrar; 200 si es el reenvío del mismo cierre (misma clave, E05-12).
@router.post(
    "/{order_id}/closure",
    response_model=ClosureTechnicianOut,
    status_code=status.HTTP_201_CREATED,
)
async def close_my_order(
    order_id: uuid.UUID,
    payload: ClosureCreate,
    session: SessionDep,
    user: CrewUser,
    response: Response,
) -> ClosureTechnicianOut:
    try:
        closure, created = await closures_service.close_order(session, user, order_id, payload)
    except work_orders_service.WorkOrderNotFoundError:
        raise _order_not_found() from None
    except closures_service.ClosureValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": exc.code, "message": exc.message, "field": exc.field},
        ) from None
    except closures_service.IdempotencyKeyReusedError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "idempotency_key_reused",
                "message": "Este cierre ya se usó en otra orden. Volvé a abrir el cierre.",
                "field": "idempotency_key",
            },
        ) from None
    if not created:
        response.status_code = status.HTTP_200_OK
    return closure


def _order_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "order_not_found", "message": "No se encontró la orden."},
    )
