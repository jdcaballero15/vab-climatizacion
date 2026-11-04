import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep, require_role
from app.api.schemas.maintenance import (
    CheckStepAdminOut,
    CheckStepCreate,
    CheckStepOrder,
    CheckStepUpdate,
    MaintenancePlanAdminOut,
    MaintenancePlanCreate,
    MaintenancePlanUpdate,
    MaintenanceRunOut,
)
from app.db.models.user import User, UserRole
from app.services import maintenance as maintenance_service
from app.services import maintenance_checklist

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
    maintenance_checklist.CheckStepNotFoundError: (
        404,
        "check_step_not_found",
        "No se encontró el paso.",
    ),
    maintenance_checklist.CheckStepNameTakenError: (
        409,
        "check_step_name_already_exists",
        "Ya hay un paso con ese nombre.",
    ),
    maintenance_checklist.CheckStepOrderMismatchError: (
        422,
        "check_step_order_mismatch",
        "La lista cambió mientras la ordenabas. Volvé a cargarla.",
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


# ---- E07-01: checklist único ----


@router.get("/check-steps", response_model=list[CheckStepAdminOut])
async def list_check_steps(
    session: SessionDep, _: AdminOnly, include_inactive: bool = False
) -> list[CheckStepAdminOut]:
    steps = await maintenance_checklist.list_steps(session, include_inactive=include_inactive)
    return [CheckStepAdminOut.model_validate(step) for step in steps]


@router.post("/check-steps", response_model=CheckStepAdminOut, status_code=status.HTTP_201_CREATED)
async def create_check_step(
    payload: CheckStepCreate, session: SessionDep, _: AdminOnly
) -> CheckStepAdminOut:
    try:
        step = await maintenance_checklist.create_step(session, payload)
    except _ERRORS as exc:
        raise _error(exc) from None
    return CheckStepAdminOut.model_validate(step)


# Antes de /{step_id}: si no, "order" se toma como un id y da 422.
@router.put("/check-steps/order", response_model=list[CheckStepAdminOut])
async def reorder_check_steps(
    payload: CheckStepOrder, session: SessionDep, _: AdminOnly
) -> list[CheckStepAdminOut]:
    try:
        steps = await maintenance_checklist.reorder_steps(session, payload)
    except _ERRORS as exc:
        raise _error(exc) from None
    return [CheckStepAdminOut.model_validate(step) for step in steps]


@router.patch("/check-steps/{step_id}", response_model=CheckStepAdminOut)
async def update_check_step(
    step_id: uuid.UUID, payload: CheckStepUpdate, session: SessionDep, _: AdminOnly
) -> CheckStepAdminOut:
    try:
        step = await maintenance_checklist.update_step(session, step_id, payload)
    except _ERRORS as exc:
        raise _error(exc) from None
    return CheckStepAdminOut.model_validate(step)


def _error(exc: Exception) -> HTTPException:
    status_code, code, message = _ERROR_DETAIL[type(exc)]
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})
