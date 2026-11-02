import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.api.schemas.closure import OtherText, Quantity

# Materiales de una orden para administración (E05-05). Llevan precios: nunca al técnico.


class MaterialLineAdminOut(BaseModel):
    id: uuid.UUID
    part_id: uuid.UUID | None
    # Nombre del material o texto escrito en "Otro".
    name: str
    unit: str | None
    is_other: bool
    quantity: Decimal
    # El estampado si la orden está aprobada; si no, el vigente. Nulo en "Otro".
    unit_price: Decimal | None
    subtotal: Decimal | None
    # Cierre de la visita en que se cargó; nulo si lo agregó administración.
    visit_closed_at: datetime | None
    added_by_name: str


class OrderMaterialsAdminOut(BaseModel):
    approved: bool
    approved_at: datetime | None
    lines: list[MaterialLineAdminOut]
    # Suma de los subtotales; las líneas "Otro" no suman hasta pasarlas a la lista.
    total: Decimal


class MaterialLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    part_id: uuid.UUID | None = None
    other_text: OtherText = None
    quantity: Quantity


class MaterialLineUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantity: Quantity


class MaterialLinePromotion(BaseModel):
    """Pasa una línea "Otro" a un material de la lista."""

    model_config = ConfigDict(extra="forbid")

    part_id: uuid.UUID
