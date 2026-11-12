import uuid
from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep, require_role
from app.api.schemas.equipment import (
    EquipmentAdminOut,
    EquipmentCreate,
    EquipmentFileOut,
    EquipmentTransferCreate,
    EquipmentUpdate,
)
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
AdminOrOwner = Annotated[User, Depends(require_role(UserRole.admin, UserRole.owner))]


@router.get("/admin/clients/{client_id}/equipment", response_model=list[EquipmentAdminOut])
async def list_equipment(
    client_id: uuid.UUID,
    session: SessionDep,
    _: AdminOnly,
    site_id: uuid.UUID | None = None,
    # Solo los dados de baja, para restaurarlos (E03-07).
    deleted: bool = False,
) -> Sequence[Equipment]:
    try:
        if deleted:
            return await equipment_service.list_deleted_equipment(session, client_id)
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


@router.get("/admin/equipment/{equipment_id}/file", response_model=EquipmentFileOut)
async def get_equipment_file(
    equipment_id: uuid.UUID, session: SessionDep, _: AdminOrOwner
) -> EquipmentFileOut:
    """Ficha con traslados y trabajos, también de un equipo dado de baja (E03-05)."""
    try:
        return await equipment_service.equipment_file(session, equipment_id)
    except equipment_service.EquipmentNotFoundError:
        raise _equipment_not_found() from None


@router.post("/admin/equipment/{equipment_id}/deactivation", response_model=EquipmentAdminOut)
async def deactivate_equipment(
    equipment_id: uuid.UUID, session: SessionDep, admin: AdminOnly
) -> Equipment:
    try:
        return await equipment_service.deactivate_equipment(session, equipment_id, admin)
    except equipment_service.EquipmentNotFoundError:
        raise _equipment_not_found() from None
    except equipment_service.EquipmentHasOpenOrdersError as exc:
        raise _error(409, "equipment_has_open_orders", exc.message) from None


@router.post("/admin/equipment/{equipment_id}/restoration", response_model=EquipmentAdminOut)
async def restore_equipment(
    equipment_id: uuid.UUID, session: SessionDep, admin: AdminOnly
) -> Equipment:
    try:
        return await equipment_service.restore_equipment(session, equipment_id, admin)
    except equipment_service.EquipmentNotFoundError:
        raise _equipment_not_found() from None
    except equipment_service.EquipmentNotDeletedError:
        raise _error(409, "equipment_not_deleted", "El equipo no está dado de baja.") from None


@router.post("/admin/equipment/{equipment_id}/transfer", response_model=EquipmentAdminOut)
async def transfer_equipment(
    equipment_id: uuid.UUID,
    payload: EquipmentTransferCreate,
    session: SessionDep,
    admin: AdminOnly,
) -> Equipment:
    """Pasa el equipo a un domicilio de otro cliente, con código nuevo (E03-09)."""
    try:
        return await equipment_service.transfer_equipment(session, equipment_id, payload, admin)
    except equipment_service.EquipmentNotFoundError:
        raise _equipment_not_found() from None
    except clients_service.ClientNotFoundError:
        raise _error(404, "client_not_found", "No se encontró el cliente.") from None
    except equipment_service.TransferSameClientError:
        raise _error(
            422,
            "same_client",
            "El domicilio es del mismo cliente: para eso, cambiá el domicilio del equipo.",
        ) from None
    except equipment_service.EquipmentCodeUnavailableError:
        raise _error(
            409,
            "equipment_code_unavailable",
            "No se pudo generar el código del equipo. Volvé a intentar.",
        ) from None
    except _CHOICE_ERRORS as exc:
        raise _choice_error(exc) from None


def _choice_error(exc: Exception) -> HTTPException:
    status_code, code, message = _CHOICE_ERROR_DETAIL[type(exc)]
    return _error(status_code, code, message)


def _equipment_not_found() -> HTTPException:
    return _error(404, "equipment_not_found", "No se encontró el equipo.")


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})
