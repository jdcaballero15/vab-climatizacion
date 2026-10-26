import uuid
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, StringConstraints, field_validator

from app.api.schemas.client import Notes, blank_to_none

# Obligatoria: un texto vacío pasa a None y se rechaza con 422.
LocationNote = Annotated[str, BeforeValidator(blank_to_none), StringConstraints(max_length=255)]
OptionalText = Annotated[
    Annotated[str, StringConstraints(max_length=255)] | None, BeforeValidator(blank_to_none)
]


# extra="forbid": el código lo genera el sistema; mandarlo es un error, no se ignora en silencio.
class EquipmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_site_id: uuid.UUID
    equipment_type_id: uuid.UUID
    location_note: LocationNote
    brand: OptionalText = None
    model: OptionalText = None
    serial_number: OptionalText = None
    notes: Notes = None


class EquipmentUpdate(BaseModel):
    """Solo se cambian los campos enviados; un dato opcional en null se borra."""

    model_config = ConfigDict(extra="forbid")

    client_site_id: uuid.UUID | None = None
    equipment_type_id: uuid.UUID | None = None
    location_note: LocationNote | None = None
    brand: OptionalText = None
    model: OptionalText = None
    serial_number: OptionalText = None
    notes: Notes = None

    @field_validator("client_site_id", "equipment_type_id", "location_note")
    @classmethod
    def _not_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("No puede quedar vacío.")
        return value


class EquipmentAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_site_id: uuid.UUID
    equipment_type_id: uuid.UUID
    internal_code: str
    location_note: str
    brand: str | None
    model: str | None
    serial_number: str | None
    notes: str | None
