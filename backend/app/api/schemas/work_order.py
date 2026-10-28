import uuid
from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, StringConstraints

from app.api.schemas.client import ClientSiteTechnicianOut, blank_to_none
from app.domain.work_order import (
    CancelReason,
    ClosureOutcome,
    NotDoneReason,
    OrderChannel,
    OrderKind,
    OrderSource,
    OrderStatus,
)

# Obligatoria: un texto vacío pasa a None y se rechaza con 422.
Description = Annotated[str, BeforeValidator(blank_to_none), StringConstraints(max_length=2000)]
RequesterText = Annotated[
    Annotated[str, StringConstraints(max_length=255)] | None, BeforeValidator(blank_to_none)
]
# Motivo opcional de una asignación, reasignación o desasignación (E04-04, criterio 5).
ChangeReason = Annotated[
    Annotated[str, StringConstraints(max_length=255)] | None, BeforeValidator(blank_to_none)
]
# El texto de "Otro" al cancelar: vacío o solo espacios cuenta como no cargado.
CancelReasonText = Annotated[
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
    # Opcional: un equipo del domicilio elegido (E04-12).
    equipment_id: uuid.UUID | None = None


class EquipmentChange(BaseModel):
    """El equipo de una orden Pendiente o Asignada; nulo para sacarlo (E04-12)."""

    model_config = ConfigDict(extra="forbid")

    equipment_id: uuid.UUID | None


class OrderEquipmentOut(BaseModel):
    """El equipo de la orden en el listado de la oficina (E04-12)."""

    id: uuid.UUID
    internal_code: str
    location_note: str


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
    equipment_id: uuid.UUID | None
    # Del evento de creación (ADR 0005), no de la columna técnica created_at.
    created_at: datetime


class ReturnedFromCrewOut(BaseModel):
    """Por qué volvió a Pendiente desde una escuadrilla (E05-08, criterio 5)."""

    # Para preelegirla al reprogramar (E04-04, criterio 4).
    crew_id: uuid.UUID
    crew_name: str
    closed_at: datetime
    outcome: ClosureOutcome
    not_done_reason: NotDoneReason | None
    observation: str | None


class CurrentAssignmentOut(BaseModel):
    """Escuadrilla y fecha prevista de una orden Asignada o En curso."""

    crew_name: str
    scheduled_for: date


class CancellationAdminOut(BaseModel):
    """Motivo, quién y cuándo se canceló (E04-07, criterio 6)."""

    reason: CancelReason
    reason_text: str | None
    cancelled_by_name: str
    cancelled_at: datetime


class CompletedOut(BaseModel):
    """Qué escuadrilla la terminó y cuándo (E04-08, criterio 1)."""

    crew_name: str | None
    closed_at: datetime


class OrderListItemOut(BaseModel):
    id: uuid.UUID
    number: int
    status: OrderStatus
    client_id: uuid.UUID
    client_name: str
    site_label: str | None
    site_address: str
    work_type_name: str
    description: str | None
    created_at: datetime
    # Solo en pendientes. Nulo si no volvió de una escuadrilla o si después se la reasignó.
    returned: ReturnedFromCrewOut | None
    # Solo en Asignadas y En curso.
    assignment: CurrentAssignmentOut | None
    # Solo en canceladas.
    cancellation: CancellationAdminOut | None
    # Solo en terminadas.
    completed: CompletedOut | None
    # Nulo si la orden no tiene equipo (E04-12).
    equipment: OrderEquipmentOut | None


class OrderListPage(BaseModel):
    items: list[OrderListItemOut]
    total: int
    limit: int
    offset: int


# extra="forbid": el estado y quién cancela los pone el sistema.
class CancellationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: CancelReason
    # Obligatorio con "Otro" y solo con "Otro" (lo valida el servicio, con el campo).
    reason_text: CancelReasonText = None


class AssignmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    crew_id: uuid.UUID
    # Solo el día, sin hora ni franja (decisión de E04-03).
    scheduled_for: date
    reason: ChangeReason = None


class UnassignmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: ChangeReason = None


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


class DoneOrderTechnicianOut(BaseModel):
    """Un cierre de la escuadrilla en "Hechas esta semana" (E05-14): solo el resultado."""

    id: uuid.UUID
    number: int
    work_type_name: str
    description: str | None
    client_name: str
    address: str
    outcome: ClosureOutcome
    not_done_reason: NotDoneReason | None
    closed_at: datetime


class CrewDoneOrdersTechnicianOut(BaseModel):
    # Nulo si el usuario no tiene una escuadrilla activa, como en "Para hacer".
    crew: CrewTechnicianOut | None
    orders: list[DoneOrderTechnicianOut]


class CrewOrdersTechnicianOut(BaseModel):
    # Nulo si el usuario no tiene una escuadrilla activa (criterio 7).
    crew: CrewTechnicianOut | None
    # Día de hoy en Argentina: el celular calcula "Hoy" y "Vencida" con este, no con su reloj.
    today: date
    orders: list[OrderTechnicianOut]
