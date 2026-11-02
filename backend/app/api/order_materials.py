import uuid
from collections.abc import Awaitable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep, require_role
from app.api.schemas.order_materials import (
    MaterialLineCreate,
    MaterialLinePromotion,
    MaterialLineUpdate,
    OrderMaterialsAdminOut,
)
from app.db.models.user import User, UserRole
from app.services import order_materials as materials_service
from app.services import work_orders as work_orders_service

router = APIRouter(prefix="/admin/orders", tags=["órdenes"])

# Solo administración ve precios y corrige materiales (regla 1, E05-05).
AdminOnly = Annotated[User, Depends(require_role(UserRole.admin))]

_CONFLICTS = (
    materials_service.OrderApprovedError,
    materials_service.OrderNotEditableError,
    materials_service.OrderNotDoneError,
    materials_service.OtherMaterialsPendingError,
    materials_service.LineNotOtherError,
)


@router.get("/{order_id}/materials", response_model=OrderMaterialsAdminOut)
async def get_order_materials(
    order_id: uuid.UUID, session: SessionDep, _: AdminOnly
) -> OrderMaterialsAdminOut:
    return await _run(materials_service.get_materials(session, order_id))


@router.post(
    "/{order_id}/materials",
    response_model=OrderMaterialsAdminOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_material_line(
    order_id: uuid.UUID, payload: MaterialLineCreate, session: SessionDep, admin: AdminOnly
) -> OrderMaterialsAdminOut:
    return await _run(materials_service.add_line(session, order_id, payload, admin))


@router.patch("/{order_id}/materials/{line_id}", response_model=OrderMaterialsAdminOut)
async def update_material_line(
    order_id: uuid.UUID,
    line_id: uuid.UUID,
    payload: MaterialLineUpdate,
    session: SessionDep,
    admin: AdminOnly,
) -> OrderMaterialsAdminOut:
    return await _run(materials_service.update_line(session, order_id, line_id, payload, admin))


# Sacar es borrado lógico: la línea queda con deleted_at y un evento en la línea de tiempo.
@router.post("/{order_id}/materials/{line_id}/removal", response_model=OrderMaterialsAdminOut)
async def remove_material_line(
    order_id: uuid.UUID, line_id: uuid.UUID, session: SessionDep, admin: AdminOnly
) -> OrderMaterialsAdminOut:
    return await _run(materials_service.remove_line(session, order_id, line_id, admin))


@router.post("/{order_id}/materials/{line_id}/promotion", response_model=OrderMaterialsAdminOut)
async def promote_material_line(
    order_id: uuid.UUID,
    line_id: uuid.UUID,
    payload: MaterialLinePromotion,
    session: SessionDep,
    admin: AdminOnly,
) -> OrderMaterialsAdminOut:
    return await _run(materials_service.promote_line(session, order_id, line_id, payload, admin))


@router.post("/{order_id}/approval", response_model=OrderMaterialsAdminOut)
async def approve_order(
    order_id: uuid.UUID, session: SessionDep, admin: AdminOnly
) -> OrderMaterialsAdminOut:
    return await _run(materials_service.approve(session, order_id, admin))


async def _run(call: Awaitable[OrderMaterialsAdminOut]) -> OrderMaterialsAdminOut:
    try:
        return await call
    except work_orders_service.WorkOrderNotFoundError:
        raise _error(404, "order_not_found", "No se encontró la orden.") from None
    except materials_service.MaterialLineNotFoundError:
        raise _error(
            404, "material_line_not_found", "No se encontró ese material en la orden."
        ) from None
    except materials_service.MaterialLineInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": exc.code, "message": exc.message, "field": "part_id"},
        ) from None
    except _CONFLICTS as exc:
        raise _error(409, exc.code, exc.message) from None


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})
