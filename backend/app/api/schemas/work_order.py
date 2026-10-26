import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, StringConstraints

from app.api.schemas.client import ClientSiteTechnicianOut, blank_to_none
from app.domain.work_order import OrderChannel, OrderKind, OrderSource, OrderStatus

# Obligatoria: un texto vacío pasa a None y se rechaza con 422.
Description = Annotated[str, BeforeValidator(blank_to_none), StringConstraints(max_length=2000)]
RequesterText = Annotated[
    Annotated[str, StringConstraints(max_length=255)] | None, BeforeValidator(blank_to_none)
]


# extra="forbid": número y estado los pone el sistema; mandarlos es un error.
class WorkOrderCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: uuid.UUID
    client_site_id: uuid.UUID
    work_type_id: uuid.UUID
    channel: OrderChannel
    description: Description
    requester_name: RequesterText = None
    requester_area: RequesterText = None


class WorkOrderAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: int
    kind: OrderKind
    source: OrderSource
    status: OrderStatus
    client_id: uuid.UUID
    client_site_id: uuid.UUID
    work_type_id: uuid.UUID
    channel: OrderChannel | None
    description: str | None
    requester_name: str | None
    requester_area: str | None
    # Del evento de creación (ADR 0005), no de la columna técnica created_at.
    created_at: datetime


class PendingOrderOut(BaseModel):
    id: uuid.UUID
    number: int
    client_id: uuid.UUID
    client_name: str
    site_label: str | None
    site_address: str
    work_type_name: str
    description: str | None
    created_at: datetime


class PendingOrderPage(BaseModel):
    items: list[PendingOrderOut]
    total: int
    limit: int
    offset: int


class AssignmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    crew_id: uuid.UUID
    # Solo el día, sin hora ni franja (decisión de E04-03).
    scheduled_for: date


class AssignmentAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    work_order_id: uuid.UUID
    crew_id: uuid.UUID
    scheduled_for: date
    assigned_at: datetime


# E05-01: lo que ve la escuadrilla en el celular. Sin quién pidió, canal ni precios (ADR 0006).
class EquipmentTechnicianOut(BaseModel):
    location_note: str
    equipment_type_name: str
    brand: str | None
    model: str | None


class OrderTechnicianOut(BaseModel):
    id: uuid.UUID
    number: int
    status: OrderStatus
    work_type_name: str
    description: str | None
    client_name: str
    scheduled_for: date
    site: ClientSiteTechnicianOut
    equipment: EquipmentTechnicianOut | None


class OrderDetailTechnicianOut(OrderTechnicianOut):
    """Detalle de una orden abierta de la escuadrilla (E05-02). Sin historial ni quién pidió."""

    # Dónde se pidió (sector, piso o ala); quién pidió no llega al técnico.
    requester_area: str | None
    # Tareas activas del tipo de trabajo, de solo lectura: se tildan al cerrar (E05-04).
    tasks: list[str]
    today: date


class CrewTechnicianOut(BaseModel):
    name: str


class CrewOrdersTechnicianOut(BaseModel):
    # Nulo si el usuario no tiene una escuadrilla activa (criterio 7).
    crew: CrewTechnicianOut | None
    # Día de hoy en Argentina: el celular calcula "Hoy" y "Vencida" con este, no con su reloj.
    today: date
    orders: list[OrderTechnicianOut]
