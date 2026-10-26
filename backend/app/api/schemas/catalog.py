import uuid
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, StringConstraints


def _normalize_name(value: Any) -> Any:
    # Recorta y colapsa espacios: "  Carga   de gas " se guarda como "Carga de gas".
    return " ".join(value.split()) if isinstance(value, str) else value


CatalogName = Annotated[
    str, BeforeValidator(_normalize_name), StringConstraints(min_length=1, max_length=255)
]


class WorkTypeCreate(BaseModel):
    name: CatalogName


class WorkTypeUpdate(BaseModel):
    name: CatalogName | None = None
    is_active: bool | None = None


class WorkTypeAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    is_active: bool


class TaskCreate(BaseModel):
    name: CatalogName


class TaskUpdate(BaseModel):
    name: CatalogName | None = None
    is_active: bool | None = None


class TaskAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    work_type_id: uuid.UUID
    name: str
    is_active: bool
