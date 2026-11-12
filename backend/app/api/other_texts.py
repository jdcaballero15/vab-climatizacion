import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, BeforeValidator, ConfigDict, StringConstraints

from app.api.deps import SessionDep, require_role
from app.api.schemas.client import blank_to_none
from app.db.models.user import User, UserRole
from app.services import catalog as catalog_service
from app.services import other_texts as other_texts_service
from app.services import parts as parts_service
from app.services.other_texts import Kind

router = APIRouter(prefix="/admin/other-texts", tags=["catálogos"])

AdminOnly = Annotated[User, Depends(require_role(UserRole.admin))]
Name = Annotated[
    str | None,
    BeforeValidator(blank_to_none),
    StringConstraints(strip_whitespace=True, max_length=255),
]

_NAME_TAKEN = (
    catalog_service.FailureNameAlreadyExistsError,
    catalog_service.RepairNameAlreadyExistsError,
    parts_service.PartNameAlreadyExistsError,
)


class OtherTextOut(BaseModel):
    text_key: str
    text: str
    count: int


class PromoteRequest(BaseModel):
    """Sumar un texto a la lista: con target_id, a un valor que ya existe; si no, uno
    nuevo con name (por defecto el texto). Una reparación nueva necesita su falla."""

    model_config = ConfigDict(extra="forbid")

    kind: Kind
    text_key: Annotated[str, StringConstraints(min_length=1, max_length=255)]
    name: Name = None
    target_id: uuid.UUID | None = None
    failure_id: uuid.UUID | None = None
    equipment_type_id: uuid.UUID | None = None
    unit: Name = None


class DismissRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Kind
    text_key: Annotated[str, StringConstraints(min_length=1, max_length=255)]


class PromoteOut(BaseModel):
    updated: int


@router.get("", response_model=list[OtherTextOut])
async def list_other_texts(session: SessionDep, _: AdminOnly, kind: Kind) -> list[OtherTextOut]:
    """Textos de "Otro" con sus repeticiones, el más repetido primero (E02-07)."""
    return [
        OtherTextOut(text_key=t.text_key, text=t.text, count=t.count)
        for t in await other_texts_service.list_texts(session, kind)
    ]


@router.post("/promote", response_model=PromoteOut)
async def promote_other_text(
    payload: PromoteRequest, session: SessionDep, admin: AdminOnly
) -> PromoteOut:
    try:
        updated = await other_texts_service.promote(
            session,
            payload.kind,
            payload.text_key,
            name=payload.name,
            target_id=payload.target_id,
            failure_id=payload.failure_id,
            equipment_type_id=payload.equipment_type_id,
            unit=payload.unit,
            actor=admin,
        )
    except other_texts_service.TargetNotFoundError:
        raise _error(404, "target_not_found", "No se encontró el valor de la lista.") from None
    except _NAME_TAKEN:
        raise _error(
            409,
            "name_already_exists",
            "Ya existe en la lista: elegilo como valor existente.",
        ) from None
    return PromoteOut(updated=updated)


@router.post("/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_other_text(payload: DismissRequest, session: SessionDep, _: AdminOnly) -> None:
    """Deja de mostrar el texto en la revisión; las órdenes lo conservan (criterio 3)."""
    await other_texts_service.dismiss(session, payload.kind, payload.text_key)


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})
