import uuid
from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep, require_role
from app.api.schemas.crew import (
    CrewAdminOut,
    CrewCreate,
    CrewUpdate,
    FieldTechnicianAdminOut,
    FieldTechnicianCreate,
    FieldTechnicianUpdate,
)
from app.db.models.crew import Crew, FieldTechnician
from app.db.models.user import User, UserRole
from app.services import crews as crews_service

router = APIRouter(prefix="/admin/crews", tags=["escuadrillas"])
technicians_router = APIRouter(prefix="/admin/field-technicians", tags=["escuadrillas"])

# Solo administración gestiona escuadrillas y técnicos (roles-permisos.md, D-013).
AdminOnly = Annotated[User, Depends(require_role(UserRole.admin))]

_ERROR_DETAIL: dict[type[Exception], tuple[int, str, str]] = {
    crews_service.CrewNotFoundError: (404, "crew_not_found", "No se encontró la escuadrilla."),
    crews_service.CrewNameAlreadyExistsError: (
        409,
        "crew_name_already_exists",
        "Ya existe una escuadrilla con ese nombre (puede estar desactivada).",
    ),
    crews_service.CrewUserNotAvailableError: (
        422,
        "crew_user_not_available",
        "Elegí un usuario técnico activo que no sea de otra escuadrilla.",
    ),
    crews_service.FieldTechnicianNotFoundError: (
        404,
        "field_technician_not_found",
        "No se encontró el técnico.",
    ),
    crews_service.FieldTechnicianNameAlreadyExistsError: (
        409,
        "field_technician_name_already_exists",
        "Ya existe un técnico con ese nombre (puede estar desactivado).",
    ),
}
_ERRORS = tuple(_ERROR_DETAIL)


@router.get("", response_model=list[CrewAdminOut])
async def list_crews(
    session: SessionDep, _: AdminOnly, include_inactive: bool = False
) -> Sequence[Crew]:
    return await crews_service.list_crews(session, include_inactive=include_inactive)


@router.post("", response_model=CrewAdminOut, status_code=status.HTTP_201_CREATED)
async def create_crew(payload: CrewCreate, session: SessionDep, _: AdminOnly) -> Crew:
    try:
        return await crews_service.create_crew(session, payload)
    except _ERRORS as exc:
        raise _error(exc) from None


@router.get("/{crew_id}", response_model=CrewAdminOut)
async def get_crew(crew_id: uuid.UUID, session: SessionDep, _: AdminOnly) -> Crew:
    try:
        return await crews_service.get_crew(session, crew_id)
    except _ERRORS as exc:
        raise _error(exc) from None


@router.patch("/{crew_id}", response_model=CrewAdminOut)
async def update_crew(
    crew_id: uuid.UUID, payload: CrewUpdate, session: SessionDep, _: AdminOnly
) -> Crew:
    try:
        return await crews_service.update_crew(session, crew_id, payload)
    except _ERRORS as exc:
        raise _error(exc) from None


@technicians_router.get("", response_model=list[FieldTechnicianAdminOut])
async def list_field_technicians(
    session: SessionDep, _: AdminOnly, include_inactive: bool = False
) -> Sequence[FieldTechnician]:
    return await crews_service.list_field_technicians(session, include_inactive=include_inactive)


@technicians_router.post(
    "", response_model=FieldTechnicianAdminOut, status_code=status.HTTP_201_CREATED
)
async def create_field_technician(
    payload: FieldTechnicianCreate, session: SessionDep, _: AdminOnly
) -> FieldTechnician:
    try:
        return await crews_service.create_field_technician(session, payload)
    except _ERRORS as exc:
        raise _error(exc) from None


@technicians_router.patch("/{technician_id}", response_model=FieldTechnicianAdminOut)
async def update_field_technician(
    technician_id: uuid.UUID,
    payload: FieldTechnicianUpdate,
    session: SessionDep,
    _: AdminOnly,
) -> FieldTechnician:
    try:
        return await crews_service.update_field_technician(session, technician_id, payload)
    except _ERRORS as exc:
        raise _error(exc) from None


def _error(exc: Exception) -> HTTPException:
    status_code, code, message = _ERROR_DETAIL[type(exc)]
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})
