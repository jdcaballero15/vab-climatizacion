import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, StringConstraints

from app.api.schemas.catalog import CatalogName, _normalize_name
from app.api.schemas.work_order import Amount

# kg, metro, unidad: texto libre corto, con las mismas reglas de espacios que los nombres.
PartUnit = Annotated[
    str, BeforeValidator(_normalize_name), StringConstraints(min_length=1, max_length=20)
]


class PartCreate(BaseModel):
    name: CatalogName
    unit: PartUnit = "unidad"


class PartUpdate(BaseModel):
    name: CatalogName | None = None
    unit: PartUnit | None = None
    is_active: bool | None = None


class PartPriceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    list_price: Amount


class PartAdminOut(BaseModel):
    """Material con su precio de lista vigente (E02-05, E02-06). Solo administración."""

    id: uuid.UUID
    name: str
    unit: str
    is_active: bool
    list_price: Decimal
    price_updated_at: datetime


# E05-05: lo que la escuadrilla elige al cerrar. Nunca el precio.
class PartChoiceTechnicianOut(BaseModel):
    id: uuid.UUID
    name: str
    unit: str
