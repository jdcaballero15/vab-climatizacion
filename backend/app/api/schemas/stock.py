import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints

from app.api.schemas.client import blank_to_none
from app.db.models.stock import StockLocationKind, StockMovementKind

Name = Annotated[
    str, BeforeValidator(blank_to_none), StringConstraints(strip_whitespace=True, max_length=255)
]
Reason = Annotated[
    str, BeforeValidator(blank_to_none), StringConstraints(strip_whitespace=True, max_length=255)
]
# Como la cantidad de un material (E05-05): mayor que cero, hasta tres decimales.
Quantity = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=3)]
# El ajuste puede restar: distinto de cero, se valida en el servicio.
SignedQuantity = Annotated[Decimal, Field(max_digits=12, decimal_places=3)]


class LocationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: StockLocationKind
    name: Name
    # Solo camionetas: la escuadrilla que anda en ella (E08-01, criterio 2).
    crew_id: uuid.UUID | None = None


class LocationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Name | None = None
    crew_id: uuid.UUID | None = None
    is_active: bool | None = None


class LocationOut(BaseModel):
    id: uuid.UUID
    kind: StockLocationKind
    name: str
    crew_id: uuid.UUID | None
    crew_name: str | None
    is_active: bool


class ReceiptCreate(BaseModel):
    """Ingreso de repuestos a una ubicación (E08-02)."""

    model_config = ConfigDict(extra="forbid")

    part_id: uuid.UUID
    location_id: uuid.UUID
    quantity: Quantity


class TransferCreate(BaseModel):
    """De una ubicación a otra en una sola transacción (E08-03)."""

    model_config = ConfigDict(extra="forbid")

    part_id: uuid.UUID
    from_location_id: uuid.UUID
    to_location_id: uuid.UUID
    quantity: Quantity


class AdjustmentCreate(BaseModel):
    """Corrección de inventario con motivo; positiva suma y negativa resta (E08-06)."""

    model_config = ConfigDict(extra="forbid")

    part_id: uuid.UUID
    location_id: uuid.UUID
    quantity: SignedQuantity
    reason: Reason


class StockBalanceOut(BaseModel):
    """Cuánto hay de un repuesto en una ubicación. Negativo: hubo usos sin stock (E08-08)."""

    part_id: uuid.UUID
    part_name: str
    unit: str
    location_id: uuid.UUID
    location_name: str
    quantity: Decimal


class StockPartOut(BaseModel):
    part_id: uuid.UUID
    part_name: str
    unit: str
    total: Decimal
    by_location: list[StockBalanceOut]
    # Alguna ubicación quedó en negativo: hay que ajustarla (E08-08, criterio 2).
    has_negative: bool


class MovementOut(BaseModel):
    """Un movimiento en el historial del repuesto (E08-07)."""

    id: uuid.UUID
    kind: StockMovementKind
    quantity: Decimal
    from_location_name: str | None
    to_location_name: str | None
    work_order_id: uuid.UUID | None
    work_order_number: int | None
    reason: str | None
    created_by_name: str
    occurred_at: datetime


class TruckStockTechnicianOut(BaseModel):
    """Lo que hay en la camioneta de la escuadrilla, sin precios (E08-04, criterio 4)."""

    location_name: str | None
    items: list["TruckItemTechnicianOut"]


class TruckItemTechnicianOut(BaseModel):
    part_name: str
    unit: str
    quantity: Decimal


TruckStockTechnicianOut.model_rebuild()
