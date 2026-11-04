import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep, require_role
from app.api.schemas.maintenance import (
    MaintenancePlanAdminOut,
    MaintenancePlanCreate,
    MaintenancePlanUpdate,
    MaintenanceRunOut,
)
from app.db.models.user import User, UserRole
from app.services import maintenance as maintenance_service

router = APIRouter(prefix="/admin/maintenance", tags=["mantenimiento"])

# Solo administración gestiona los abonos (roles-permisos.md).
AdminOnly = Annotated[User, Depends(require_role(UserRole.admin))]

_ERROR_DETAIL: dict[type[Exception], tuple[int, str, str]] = {
    maintenance_service.PlanNotFoundError: (404, "plan_not_found", "No se encontró el plan."),
    maintenance_service.PlanEquipmentNotAvailableError: (
        422,
        "equipment_not_available",
        "Elegí un equipo que no esté dado de baja.",
    ),
    maintenance_service.PlanWorkTypeNotAvailableError: (
        422,
        "work_type_not_available",
        "Elegí un tipo de trabajo activo.",
    ),
    maintenance_service.PlanCrewNotAvailableError: (
        422,
        "crew_not_available",
        "Elegí una escuadrilla activa.",
    ),
    maintenance_service.EquipmentAlreadyInPlanError: (
        409,
        "equipment_already_in_plan",
        "Ese equipo ya tiene un plan de mantenimiento activo.",
    ),
}
_ERRORS = tuple(_ERROR_DETAIL)


@router.get("/plans", response_model=list[MaintenancePlanAdminOut])
async def list_plans(
    session: SessionDep,
    _: AdminOnly,
    include_ended: bool = False,
    equipment_id: uuid.UUID | None = None,
    client_id: uuid.UUID | None = None,
) -> list[MaintenancePlanAdminOut]:
    return await maintenance_service.list_plans(
        session, include_ended=include_ended, equipment_id=equipment_id, client_id=client_id
    )


@router.post("/plans", response_model=MaintenancePlanAdminOut, status_code=status.HTTP_201_CREATED)
async def create_plan(
    payload: MaintenancePlanCreate, session: SessionDep, _: AdminOnly
) -> MaintenancePlanAdminOut:
    try:
        return await maintenance_service.create_plan(session, payload)
    except _ERRORS as exc:
        raise _error(exc) from None


@router.get("/plans/{plan_id}", response_model=MaintenancePlanAdminOut)
async def get_plan(
    plan_id: uuid.UUID, session: SessionDep, _: AdminOnly
) -> MaintenancePlanAdminOut:
    try:
        return await maintenance_service.get_plan(session, plan_id)
    except _ERRORS as exc:
        raise _error(exc) from None


@router.patch("/plans/{plan_id}", response_model=MaintenancePlanAdminOut)
async def update_plan(
    plan_id: uuid.UUID, payload: MaintenancePlanUpdate, session: SessionDep, _: AdminOnly
) -> MaintenancePlanAdminOut:
    try:
        return await maintenance_service.update_plan(session, plan_id, payload)
    except _ERRORS as exc:
        raise _error(exc) from None


@router.post("/run", response_model=MaintenanceRunOut)
async def run_now(session: SessionDep, _: AdminOnly) -> MaintenanceRunOut:
    """La misma corrida del cron de cada mañana, a pedido ("Generar ahora")."""
    return await maintenance_service.run_generation(session)


def _error(exc: Exception) -> HTTPException:
    status_code, code, message = _ERROR_DETAIL[type(exc)]
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})
