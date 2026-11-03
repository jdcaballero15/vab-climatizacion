import uuid

from pydantic import BaseModel


class ClientSearchOut(BaseModel):
    """Un cliente encontrado (E03-06), con un domicilio para reconocerlo."""

    id: uuid.UUID
    number: str
    name: str
    address: str | None
    deleted: bool


class EquipmentSearchOut(BaseModel):
    """Un equipo encontrado (E03-06), con su cliente y domicilio."""

    id: uuid.UUID
    internal_code: str
    location_note: str
    equipment_type_name: str
    brand: str | None
    model: str | None
    client_id: uuid.UUID
    client_name: str
    site_label: str | None
    site_address: str
    deleted: bool


class SearchOut(BaseModel):
    clients: list[ClientSearchOut]
    equipment: list[EquipmentSearchOut]
