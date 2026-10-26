import uuid
from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep, require_role
from app.api.schemas.equipment import EquipmentAdminOut, EquipmentCreate, EquipmentUpdate
from app.db.models.equipment import Equipment
from app.db.models.user import User, UserRole
from app.services import clients as clients_service
from app.services import equipment as equipment_service

router = APIRouter(tags=["equipos"])

# Errores del domicilio o el tipo elegidos, al crear o al editar.
_CHOICE_ERROR_DETAIL: dict[type[Exception], tuple[int, str, str]] = {
    clients_service.SiteNotFoundError: (404, "site_not_found", "No se encontró el domicilio."),
    clients_service.SiteOfAnotherClientError: (
        422,
        "site_of_another_client",
        "El domicilio es de otro cliente.",
    ),
    clients_service.SiteInactiveError: (422, "site_inactive", "El domicilio está desactivado."),
    equipment_service.EquipmentTypeNotFoundError: (
        404,
        "equipment_type_not_found",
        "No se encontró el tipo de equipo.",
    ),
    equipment_service.EquipmentTypeInactiveError: (
        422,
        "equipment_type_inactive",
        "El tipo de equipo está desactivado.",
    ),
}
_CHOICE_ERRORS = tuple(_CHOICE_ERROR_DETAIL)

# Solo administración gestiona equipos; dirección los ve en la ficha (E03-05).
AdminOnly = Annotated[User, Depends(require_role(UserRole.admin))]


@router.get("/admin/clients/{client_id}/equipment", response_model=list[EquipmentAdminOut])
async def list_equipment(
    client_id: uuid.UUID,
    session: SessionDep,
    _: AdminOnly,
    site_id: uuid.UUID | None = None,
) -> Sequence[Equipment]:
    try:
        return await equipment_service.list_equipment(session, client_id, site_id=site_id)
    except clients_service.ClientNotFoundError:
        raise _error(404, "client_not_found", "No se encontró el cliente.") from None


@router.post(
    "/admin/clients/{client_id}/equipment",
    response_model=EquipmentAdminOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_equipment(
    client_id: uuid.UUID, payload: EquipmentCreate, session: SessionDep, _: AdminOnly
) -> Equipment:
    try:
        return await equipment_service.create_equipment(session, client_id, payload)
    except clients_service.ClientNotFoundError:
        raise _error(404, "client_not_found", "No se encontró el cliente.") from None
    except equipment_service.EquipmentCodeUnavailableError:
        raise _error(
            409,
            "equipment_code_unavailable",
            "No se pudo generar el código del equipo. Volvé a intentar.",
        ) from None
    except _CHOICE_ERRORS as exc:
        raise _choice_error(exc) from None


@router.get("/admin/equipment/{equipment_id}", response_model=EquipmentAdminOut)
async def get_equipment(equipment_id: uuid.UUID, session: SessionDep, _: AdminOnly) -> Equipment:
    try:
        return await equipment_service.get_equipment(session, equipment_id)
    except equipment_service.EquipmentNotFoundError:
        raise _equipment_not_found() from None


@router.patch("/admin/equipment/{equipment_id}", response_model=EquipmentAdminOut)
async def update_equipment(
    equipment_id: uuid.UUID, payload: EquipmentUpdate, session: SessionDep, _: AdminOnly
) -> Equipment:
    try:
        return await equipment_service.update_equipment(session, equipment_id, payload)
    except equipment_service.EquipmentNotFoundError:
        raise _equipment_not_found() from None
    except _CHOICE_ERRORS as exc:
        raise _choice_error(exc) from None


def _choice_error(exc: Exception) -> HTTPException:
    status_code, code, message = _CHOICE_ERROR_DETAIL[type(exc)]
    return _error(status_code, code, message)


def _equipment_not_found() -> HTTPException:
    return _error(404, "equipment_not_found", "No se encontró el equipo.")


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})
