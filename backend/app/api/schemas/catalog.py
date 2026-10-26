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


class EquipmentTypeCreate(BaseModel):
    name: CatalogName


class EquipmentTypeUpdate(BaseModel):
    name: CatalogName | None = None
    is_active: bool | None = None


class EquipmentTypeAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    is_active: bool


class FailureCreate(BaseModel):
    name: CatalogName
    # Sin tipo de equipo, la falla es genérica y aplica a todos.
    equipment_type_id: uuid.UUID | None = None


class FailureUpdate(BaseModel):
    name: CatalogName | None = None
    is_active: bool | None = None


class FailureAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    equipment_type_id: uuid.UUID | None
    name: str
    is_active: bool
