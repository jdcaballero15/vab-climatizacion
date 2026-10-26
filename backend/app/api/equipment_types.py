import uuid
from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep, require_role
from app.api.schemas.catalog import (
    EquipmentTypeAdminOut,
    EquipmentTypeCreate,
    EquipmentTypeUpdate,
)
from app.db.models.catalog import EquipmentType
from app.db.models.user import User, UserRole
from app.services import catalog as catalog_service

router = APIRouter(prefix="/admin/equipment-types", tags=["catálogos"])

# Solo administración edita catálogos (ver roles-permisos.md).
AdminOnly = Annotated[User, Depends(require_role(UserRole.admin))]


@router.get("", response_model=list[EquipmentTypeAdminOut])
async def list_equipment_types(
    session: SessionDep, _: AdminOnly, include_inactive: bool = False
) -> Sequence[EquipmentType]:
    return await catalog_service.list_equipment_types(session, include_inactive=include_inactive)


@router.post("", response_model=EquipmentTypeAdminOut, status_code=status.HTTP_201_CREATED)
async def create_equipment_type(
    payload: EquipmentTypeCreate, session: SessionDep, _: AdminOnly
) -> EquipmentType:
    try:
        return await catalog_service.create_equipment_type(session, payload)
    except catalog_service.EquipmentTypeNameAlreadyExistsError:
        raise _name_taken() from None


@router.get("/{equipment_type_id}", response_model=EquipmentTypeAdminOut)
async def get_equipment_type(
    equipment_type_id: uuid.UUID, session: SessionDep, _: AdminOnly
) -> EquipmentType:
    try:
        return await catalog_service.get_equipment_type(session, equipment_type_id)
    except catalog_service.EquipmentTypeNotFoundError:
        raise _not_found() from None


@router.patch("/{equipment_type_id}", response_model=EquipmentTypeAdminOut)
async def update_equipment_type(
    equipment_type_id: uuid.UUID, payload: EquipmentTypeUpdate, session: SessionDep, _: AdminOnly
) -> EquipmentType:
    try:
        return await catalog_service.update_equipment_type(session, equipment_type_id, payload)
    except catalog_service.EquipmentTypeNotFoundError:
        raise _not_found() from None
    except catalog_service.EquipmentTypeNameAlreadyExistsError:
        raise _name_taken() from None


def _not_found() -> HTTPException:
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
            "code": "equipment_type_name_already_exists",
            "message": "Ya existe un tipo de equipo con ese nombre (puede estar desactivado).",
        },
    )
