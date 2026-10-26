import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep, require_role
from app.api.schemas.work_order import CrewOrdersTechnicianOut, OrderDetailTechnicianOut
from app.db.models.user import User, UserRole
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "order_not_found", "message": "No se encontró la orden."},
        ) from None
