import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import SessionDep, require_role
from app.api.schemas.dashboard import DashboardOut
from app.db.models.user import User, UserRole
from app.services import dashboard as dashboard_service

router = APIRouter(prefix="/admin/dashboard", tags=["tablero"])

# Dirección y administración (roles-permisos.md); el técnico no (E10-02, criterio 2).
AdminOrOwner = Annotated[User, Depends(require_role(UserRole.admin, UserRole.owner))]
_MAX_DAYS = 400


@router.get("", response_model=DashboardOut)
async def get_dashboard(
    session: SessionDep,
    _: AdminOrOwner,
    date_from: date | None = None,
    date_to: date | None = None,
    client_id: uuid.UUID | None = None,
    crew_id: uuid.UUID | None = None,
    work_type_id: uuid.UUID | None = None,
    equipment_type_id: uuid.UUID | None = None,
    compare_from: date | None = None,
    compare_to: date | None = None,
) -> DashboardOut:
    """Todos los indicadores con los mismos filtros; sin período, los últimos 30 días."""
    default_from, default_to = dashboard_service.default_period()
    start, end = date_from or default_from, date_to or default_to
    compare = (compare_from, compare_to) if compare_from and compare_to else None
    for first, last in ((start, end), *([compare] if compare else [])):
        if first > last or (last - first).days > _MAX_DAYS:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "invalid_period",
                    "message": "Elegí un período válido, de hasta 400 días.",
                },
            )
    filters = dashboard_service.DashboardFilters(
        date_from=start,
        date_to=end,
        client_id=client_id,
        crew_id=crew_id,
        work_type_id=work_type_id,
        equipment_type_id=equipment_type_id,
    )
    return await dashboard_service.build(session, filters, compare)
