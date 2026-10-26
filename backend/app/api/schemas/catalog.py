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


class EquipmentScopedCreate(BaseModel):
    name: CatalogName
    # Sin tipo de equipo, el valor es genérico y aplica a todos.
    equipment_type_id: uuid.UUID | None = None


class EquipmentScopedUpdate(BaseModel):
    name: CatalogName | None = None
    is_active: bool | None = None


class EquipmentScopedAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    equipment_type_id: uuid.UUID | None
    name: str
    is_active: bool


# Una clase por catálogo para que la API (y el cliente generado) los nombre por separado.
class FailureCreate(EquipmentScopedCreate):
    pass


class FailureUpdate(EquipmentScopedUpdate):
    pass


class FailureAdminOut(EquipmentScopedAdminOut):
    pass


class RepairCreate(EquipmentScopedCreate):
    # La falla a la que pertenece. Tiene que aplicar al tipo de la reparación.
    failure_id: uuid.UUID


class RepairUpdate(EquipmentScopedUpdate):
    pass


class RepairAdminOut(EquipmentScopedAdminOut):
    failure_id: uuid.UUID
