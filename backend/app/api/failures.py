import uuid
from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep, require_role
from app.api.schemas.catalog import FailureAdminOut, FailureCreate, FailureUpdate
from app.db.models.catalog import Failure
from app.db.models.user import User, UserRole
from app.services import catalog as catalog_service

router = APIRouter(prefix="/admin/failures", tags=["catálogos"])

# Solo administración edita catálogos (ver roles-permisos.md). El técnico leerá las
# fallas para cerrar órdenes por otro endpoint (E05-04).
AdminOnly = Annotated[User, Depends(require_role(UserRole.admin))]


@router.get("", response_model=list[FailureAdminOut])
async def list_failures(
    session: SessionDep,
    _: AdminOnly,
    equipment_type_id: uuid.UUID | None = None,
    include_inactive: bool = False,
) -> Sequence[Failure]:
    """Sin `equipment_type_id`, todas las fallas. Con él, las de ese tipo más las genéricas."""
    try:
        return await catalog_service.list_failures(
            session, equipment_type_id=equipment_type_id, include_inactive=include_inactive
        )
    except catalog_service.EquipmentTypeNotFoundError:
        raise _equipment_type_not_found() from None


@router.post("", response_model=FailureAdminOut, status_code=status.HTTP_201_CREATED)
async def create_failure(payload: FailureCreate, session: SessionDep, _: AdminOnly) -> Failure:
    try:
        return await catalog_service.create_failure(session, payload)
    except catalog_service.EquipmentTypeNotFoundError:
        raise _equipment_type_not_found() from None
    except catalog_service.FailureNameAlreadyExistsError:
        raise _name_taken() from None


@router.get("/{failure_id}", response_model=FailureAdminOut)
async def get_failure(failure_id: uuid.UUID, session: SessionDep, _: AdminOnly) -> Failure:
    try:
        return await catalog_service.get_failure(session, failure_id)
    except catalog_service.FailureNotFoundError:
        raise _not_found() from None


@router.patch("/{failure_id}", response_model=FailureAdminOut)
async def update_failure(
    failure_id: uuid.UUID, payload: FailureUpdate, session: SessionDep, _: AdminOnly
) -> Failure:
    try:
        return await catalog_service.update_failure(session, failure_id, payload)
    except catalog_service.FailureNotFoundError:
        raise _not_found() from None
    except catalog_service.FailureNameAlreadyExistsError:
        raise _name_taken() from None


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "failure_not_found", "message": "No se encontró la falla."},
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
            "code": "failure_name_already_exists",
            "message": "Ya existe una falla con ese nombre para ese tipo de equipo o como "
            "genérica (puede estar desactivada).",
        },
    )
