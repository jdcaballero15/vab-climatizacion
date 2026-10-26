import uuid
from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep, require_role
from app.api.schemas.catalog import RepairAdminOut, RepairCreate, RepairUpdate
from app.db.models.catalog import Repair
from app.db.models.user import User, UserRole
from app.services import catalog as catalog_service

router = APIRouter(prefix="/admin/repairs", tags=["catálogos"])

# Solo administración edita catálogos (ver roles-permisos.md). El técnico leerá las
# reparaciones para cerrar órdenes por otro endpoint (E05-04).
AdminOnly = Annotated[User, Depends(require_role(UserRole.admin))]


@router.get("", response_model=list[RepairAdminOut])
async def list_repairs(
    session: SessionDep,
    _: AdminOnly,
    equipment_type_id: uuid.UUID | None = None,
    include_inactive: bool = False,
) -> Sequence[Repair]:
    """Sin `equipment_type_id`, todas las reparaciones. Con él, las de ese tipo y las genéricas."""
    try:
        return await catalog_service.list_repairs(
            session, equipment_type_id=equipment_type_id, include_inactive=include_inactive
        )
    except catalog_service.EquipmentTypeNotFoundError:
        raise _equipment_type_not_found() from None


@router.post("", response_model=RepairAdminOut, status_code=status.HTTP_201_CREATED)
async def create_repair(payload: RepairCreate, session: SessionDep, _: AdminOnly) -> Repair:
    try:
        return await catalog_service.create_repair(session, payload)
    except catalog_service.EquipmentTypeNotFoundError:
        raise _equipment_type_not_found() from None
    except catalog_service.RepairNameAlreadyExistsError:
        raise _name_taken() from None


@router.get("/{repair_id}", response_model=RepairAdminOut)
async def get_repair(repair_id: uuid.UUID, session: SessionDep, _: AdminOnly) -> Repair:
    try:
        return await catalog_service.get_repair(session, repair_id)
    except catalog_service.RepairNotFoundError:
        raise _not_found() from None


@router.patch("/{repair_id}", response_model=RepairAdminOut)
async def update_repair(
    repair_id: uuid.UUID, payload: RepairUpdate, session: SessionDep, _: AdminOnly
) -> Repair:
    try:
        return await catalog_service.update_repair(session, repair_id, payload)
    except catalog_service.RepairNotFoundError:
        raise _not_found() from None
    except catalog_service.RepairNameAlreadyExistsError:
        raise _name_taken() from None


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "repair_not_found", "message": "No se encontró la reparación."},
    )


def _equipment_type_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "equipment_type_not_found",
            "message": "No se encontró el tipo de equipo.",
        },
    )


def _name_taken() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "repair_name_already_exists",
            "message": "Ya existe una reparación con ese nombre para ese tipo de equipo o como "
            "genérica (puede estar desactivada).",
        },
    )
