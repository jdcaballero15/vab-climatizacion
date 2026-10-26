import uuid
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    EmailStr,
    StringConstraints,
    field_validator,
)

from app.api.schemas.catalog import CatalogName
from app.db.models.client import ClientSegment, TaxCondition


def _blank_to_none(value: Any) -> Any:
    # Recorta y colapsa espacios; un texto vacío es "sin dato".
    if isinstance(value, str):
        value = " ".join(value.split())
        return value or None
    return value


TaxId = Annotated[
    Annotated[str, StringConstraints(max_length=20)] | None, BeforeValidator(_blank_to_none)
]
Notes = Annotated[
    Annotated[str, StringConstraints(max_length=2000)] | None, BeforeValidator(_blank_to_none)
]
ContactName = Annotated[
    Annotated[str, StringConstraints(max_length=255)] | None, BeforeValidator(_blank_to_none)
]
Phone = Annotated[
    Annotated[str, StringConstraints(max_length=50)] | None, BeforeValidator(_blank_to_none)
]
OptionalEmail = Annotated[EmailStr | None, BeforeValidator(_blank_to_none)]


# extra="forbid": el número lo asigna el sistema; mandarlo es un error, no se ignora en silencio.
class ClientCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: CatalogName
    segment: ClientSegment = ClientSegment.unclassified
    tax_id: TaxId = None
    tax_condition: TaxCondition | None = None
    notes: Notes = None


class ClientUpdate(BaseModel):
    """Solo se cambian los campos enviados; un campo opcional en null se borra."""

    model_config = ConfigDict(extra="forbid")

    name: CatalogName | None = None
    segment: ClientSegment | None = None
    tax_id: TaxId = None
    tax_condition: TaxCondition | None = None
    notes: Notes = None

    @field_validator("name", "segment")
    @classmethod
    def _not_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("No puede quedar vacío.")
        return value


class ClientAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: str
    name: str
    segment: ClientSegment
    tax_id: str | None
    tax_condition: TaxCondition | None
    notes: str | None


class ClientSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    number: str
    name: str
    segment: ClientSegment


class ClientPage(BaseModel):
    items: list[ClientSummaryOut]
    total: int
    limit: int
    offset: int


class ContactCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: ContactName = None
    phone: Phone = None
    email: OptionalEmail = None
    receives_monthly_report: bool = False


class ContactUpdate(BaseModel):
    """Solo se cambian los campos enviados; un campo en null se borra."""

    model_config = ConfigDict(extra="forbid")

    name: ContactName = None
    phone: Phone = None
    email: OptionalEmail = None
    receives_monthly_report: bool | None = None


class ContactAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    name: str | None
    phone: str | None
    email: str | None
    receives_monthly_report: bool
