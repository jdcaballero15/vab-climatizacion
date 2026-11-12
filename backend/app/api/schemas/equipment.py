import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, StringConstraints, field_validator

from app.api.schemas.client import Notes, blank_to_none
from app.domain.work_order import OrderStatus

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
    # Dado de baja (E03-07); se restaura desde la lista de dados de baja.
    deleted_at: datetime | None = None


class EquipmentTransferCreate(BaseModel):
    """Pasar el equipo a un domicilio activo de otro cliente (E03-09)."""

    model_config = ConfigDict(extra="forbid")

    client_site_id: uuid.UUID


class EquipmentTransferOut(BaseModel):
    from_client_name: str
    from_code: str
    to_client_name: str
    to_code: str
    transferred_by_name: str
    transferred_at: datetime


class EquipmentHistoryOrderOut(BaseModel):
    """Un trabajo del equipo en su ficha (E03-05)."""

    id: uuid.UUID
    number: int
    status: OrderStatus
    work_type_name: str
    client_name: str
    created_at: datetime
    closed_at: datetime | None
    failure: str | None
    repair: str | None
    observation: str | None
    materials: list[str]
    # De otro cliente: anterior al traslado (E03-09, criterio 3).
    before_transfer: bool
    # Importada de Persat (criterio 3).
    imported: bool


class EquipmentFileOut(BaseModel):
    """Ficha del equipo: datos, traslados y trabajos, el más nuevo primero (E03-05)."""

    equipment: EquipmentAdminOut
    client_id: uuid.UUID
    client_name: str
    client_number: str
    site_label: str | None
    site_address: str
    equipment_type_name: str
    transfers: list[EquipmentTransferOut]
    orders: list[EquipmentHistoryOrderOut]
