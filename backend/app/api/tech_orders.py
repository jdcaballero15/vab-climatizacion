import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import SessionDep, require_role
from app.api.schemas.closure import ClosureCreate, ClosureOptionsTechnicianOut, ClosureTechnicianOut
from app.api.schemas.equipment import EquipmentTechnicianCreate, EquipmentTypeTechnicianOut
from app.api.schemas.work_order import (
    CrewDoneOrdersTechnicianOut,
    CrewOrdersTechnicianOut,
    OrderDetailTechnicianOut,
)
from app.db.models.user import User, UserRole
from app.services import catalog as catalog_service
from app.services import clients as clients_service
from app.services import closures as closures_service
from app.services import equipment as equipment_service
from app.services import work_orders as work_orders_service

router = APIRouter(prefix="/tech/orders", tags=["app del técnico"])
# Lo que el celular necesita fuera de una orden: hoy, los tipos de equipo (E05-15).
catalog_router = APIRouter(prefix="/tech", tags=["app del técnico"])

# El usuario de la app es el de la escuadrilla (D-013).
CrewUser = Annotated[User, Depends(require_role(UserRole.technician))]


@router.get("", response_model=CrewOrdersTechnicianOut)
async def list_my_orders(session: SessionDep, user: CrewUser) -> CrewOrdersTechnicianOut:
    return await work_orders_service.list_for_crew_user(session, user)


# Antes de /{order_id}: si no, "done" se toma como un id y da 422.
@router.get("/done", response_model=CrewDoneOrdersTechnicianOut)
async def list_my_done_orders(session: SessionDep, user: CrewUser) -> CrewDoneOrdersTechnicianOut:
    return await work_orders_service.list_done_for_crew_user(session, user)


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


@catalog_router.get("/equipment-types", response_model=list[EquipmentTypeTechnicianOut])
async def list_equipment_types(
    session: SessionDep, _: CrewUser
) -> list[EquipmentTypeTechnicianOut]:
    types = await catalog_service.list_equipment_types(session, include_inactive=False)
    return [EquipmentTypeTechnicianOut.model_validate(item) for item in types]


_EQUIPMENT_ERRORS: dict[type[Exception], tuple[int, str, str, str | None]] = {
    work_orders_service.OrderHasEquipmentError: (
        409,
        "order_has_equipment",
        "La orden ya tiene equipo. Si no es el correcto, anotalo en la observación del cierre.",
        None,
    ),
    equipment_service.EquipmentTypeNotFoundError: (
        422,
        "equipment_type_not_found",
        "Elegí un tipo de equipo de la lista.",
        "equipment_type_id",
    ),
    equipment_service.EquipmentTypeInactiveError: (
        422,
        "equipment_type_inactive",
        "Ese tipo de equipo ya no se usa. Elegí otro.",
        "equipment_type_id",
    ),
    clients_service.SiteInactiveError: (
        422,
        "site_inactive",
        "El domicilio de la orden está desactivado. Avisale a la oficina.",
        None,
    ),
    equipment_service.EquipmentCodeUnavailableError: (
        409,
        "equipment_code_unavailable",
        "No se pudo generar el código del equipo. Probá de nuevo.",
        None,
    ),
}


@router.post(
    "/{order_id}/equipment",
    response_model=OrderDetailTechnicianOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_equipment_to_my_order(
    order_id: uuid.UUID, payload: EquipmentTechnicianCreate, session: SessionDep, user: CrewUser
) -> OrderDetailTechnicianOut:
    """La escuadrilla carga el equipo de una orden suya que no tiene (E05-15)."""
    try:
        return await work_orders_service.add_equipment_for_crew_user(
            session, user, order_id, payload
        )
    except work_orders_service.WorkOrderNotFoundError:
        raise _order_not_found() from None
    except tuple(_EQUIPMENT_ERRORS) as exc:
        status_code, code, message, field = _EQUIPMENT_ERRORS[type(exc)]
        detail = {"code": code, "message": message}
        if field is not None:
            detail["field"] = field
        raise HTTPException(status_code=status_code, detail=detail) from None


def _order_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "order_not_found", "message": "No se encontró la orden."},
    )
