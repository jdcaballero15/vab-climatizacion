import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, StringConstraints

from app.api.schemas.client import blank_to_none
from app.domain.work_order import (
    ClosureOutcome,
    EquipmentCondition,
    NoSignatureReason,
    NotDoneReason,
    OrderStatus,
)

# Texto opcional del cierre: vacío o solo espacios cuenta como no cargado.
OtherText = Annotated[
    Annotated[str, StringConstraints(max_length=255)] | None, BeforeValidator(blank_to_none)
]
Observation = Annotated[
    Annotated[str, StringConstraints(max_length=2000)] | None, BeforeValidator(blank_to_none)
]
SignerName = Annotated[
    Annotated[str, StringConstraints(max_length=120)] | None,
    BeforeValidator(blank_to_none),
]


# E05-04: lo que la escuadrilla elige al cerrar. Solo ids y nombres, nunca precios.
class ClosureChoiceTechnicianOut(BaseModel):
    id: uuid.UUID
    name: str


class FailureChoiceTechnicianOut(ClosureChoiceTechnicianOut):
    # Solo las reparaciones de esta falla que aplican al tipo de equipo de la orden.
    repairs: list[ClosureChoiceTechnicianOut]


class ClosureOptionsTechnicianOut(BaseModel):
    technicians: list[ClosureChoiceTechnicianOut]
    tasks: list[ClosureChoiceTechnicianOut]
    requires_failure_repair: bool
    failures: list[FailureChoiceTechnicianOut]


class SignatureIn(BaseModel):
    """Firma ya subida al bucket (E00-09) y el nombre de quien firma. Sin DNI (D-008)."""

    model_config = ConfigDict(extra="forbid")

    file_id: uuid.UUID
    # Vacío llega como None: el servicio lo marca con su campo (E05-07, criterio 3).
    signer_name: SignerName = None


# extra="forbid": un campo de más (por ejemplo, un precio) es un error, no se ignora.
class ClosureCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idempotency_key: uuid.UUID
    # "Requiere retiro" (needs_pickup) llega con E06-02.
    outcome: Literal["done", "needs_revisit", "not_done"]
    technician_ids: list[uuid.UUID]
    task_ids: list[uuid.UUID] = []
    failure_id: uuid.UUID | None = None
    failure_other_text: OtherText = None
    repair_id: uuid.UUID | None = None
    repair_other_text: OtherText = None
    equipment_condition: EquipmentCondition | None = None
    not_done_reason: NotDoneReason | None = None
    observation: Observation = None
    # Fotos ya subidas y confirmadas (E00-09), en el orden en que se muestran (E05-06).
    photo_ids: list[uuid.UUID] = []
    # La firma del cliente o por qué no hay: una de las dos (E05-07, D-011).
    signature: SignatureIn | None = None
    no_signature_reason: NoSignatureReason | None = None
    no_signature_text: OtherText = None


class ClosureTechnicianOut(BaseModel):
    id: uuid.UUID
    outcome: str
    # Estado de la orden después del cierre: Terminada o Pendiente.
    order_status: OrderStatus
    closed_at: datetime


class ClosurePhotoAdminOut(BaseModel):
    id: uuid.UUID
    content_type: str
    # URL firmada de corta duración (E00-09): se pide de nuevo si vence.
    url: str


class ClosureSignatureAdminOut(BaseModel):
    signer_name: str
    signed_at: datetime
    # URL firmada de corta duración (E00-09), como las fotos.
    url: str


class ClosureAdminOut(BaseModel):
    """Lo que cargó la escuadrilla al cerrar, para que administración lo revise (E04-08).

    Falla y reparación vienen como texto: el nombre del catálogo o lo escrito en "Otro".
    """

    outcome: ClosureOutcome
    closed_at: datetime
    closed_by_name: str
    crew_name: str | None
    technicians: list[str]
    tasks: list[str]
    failure: str | None
    repair: str | None
    equipment_condition: EquipmentCondition | None
    not_done_reason: NotDoneReason | None
    observation: str | None
    photos: list[ClosurePhotoAdminOut]
    # La firma, o el motivo por el que no hay. Los cierres anteriores a E05-07 no tienen ninguna.
    signature: ClosureSignatureAdminOut | None
    no_signature_reason: NoSignatureReason | None
    no_signature_text: str | None
