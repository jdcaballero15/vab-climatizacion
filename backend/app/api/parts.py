import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep, require_role
from app.api.schemas.part import PartAdminOut, PartCreate, PartPriceUpdate, PartUpdate
from app.db.models.user import User, UserRole
from app.services import parts as parts_service

router = APIRouter(prefix="/admin/parts", tags=["catálogos"])

# Solo administración ve y edita precios (regla 1). La escuadrilla recibe la lista sin
# precios dentro de las opciones del cierre (E05-05).
AdminOnly = Annotated[User, Depends(require_role(UserRole.admin))]


@router.get("", response_model=list[PartAdminOut])
async def list_parts(
    session: SessionDep, _: AdminOnly, include_inactive: bool = False
) -> list[PartAdminOut]:
    return await parts_service.list_parts(session, include_inactive=include_inactive)


@router.post("", response_model=PartAdminOut, status_code=status.HTTP_201_CREATED)
async def create_part(payload: PartCreate, session: SessionDep, admin: AdminOnly) -> PartAdminOut:
    try:
        return await parts_service.create_part(session, payload, admin)
    except parts_service.PartNameAlreadyExistsError:
        raise _name_taken() from None


@router.patch("/{part_id}", response_model=PartAdminOut)
async def update_part(
    part_id: uuid.UUID, payload: PartUpdate, session: SessionDep, _: AdminOnly
) -> PartAdminOut:
    try:
        return await parts_service.update_part(session, part_id, payload)
    except parts_service.PartNotFoundError:
        raise _not_found() from None
    except parts_service.PartNameAlreadyExistsError:
        raise _name_taken() from None


@router.put("/{part_id}/price", response_model=PartAdminOut)
async def set_part_price(
    part_id: uuid.UUID, payload: PartPriceUpdate, session: SessionDep, admin: AdminOnly
) -> PartAdminOut:
    try:
        return await parts_service.set_price(session, part_id, payload, admin)
    except parts_service.PartNotFoundError:
        raise _not_found() from None


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "part_not_found", "message": "No se encontró el material."},
    )


def _name_taken() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "part_name_already_exists",
            "message": "Ya existe un material con ese nombre (puede estar desactivado).",
        },
    )
