from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import SessionDep, require_role
from app.api.schemas.work_order import CrewOrdersTechnicianOut
from app.db.models.user import User, UserRole
from app.services import work_orders as work_orders_service

router = APIRouter(prefix="/tech/orders", tags=["app del técnico"])

# El usuario de la app es el de la escuadrilla (D-013).
CrewUser = Annotated[User, Depends(require_role(UserRole.technician))]


@router.get("", response_model=CrewOrdersTechnicianOut)
async def list_my_orders(session: SessionDep, user: CrewUser) -> CrewOrdersTechnicianOut:
    return await work_orders_service.list_for_crew_user(session, user)
