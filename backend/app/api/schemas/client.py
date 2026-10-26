import uuid
from typing import Annotated, Any
from urllib.parse import quote

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    EmailStr,
    StringConstraints,
    computed_field,
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
# Obligatoria: un texto vacío pasa a None y se rechaza con 422.
Address = Annotated[str, BeforeValidator(_blank_to_none), StringConstraints(max_length=255)]
SiteLabel = Annotated[
    Annotated[str, StringConstraints(max_length=255)] | None, BeforeValidator(_blank_to_none)
]
SiteReference = Annotated[
    Annotated[str, StringConstraints(max_length=500)] | None, BeforeValidator(_blank_to_none)
]

_MAPS_SEARCH_URL = "https://www.google.com/maps/search/?api=1&query="
# Los clientes están en la provincia; la localidad va en el texto de la dirección.
_MAPS_REGION = "Santiago del Estero"


def site_map_url(address: str) -> str:
    """Búsqueda de Google Maps; en Android abre la app de mapas predeterminada."""
    return _MAPS_SEARCH_URL + quote(f"{address}, {_MAPS_REGION}", safe="")


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

    client_site_id: uuid.UUID | None = None
    name: ContactName = None
    phone: Phone = None
    email: OptionalEmail = None
    receives_monthly_report: bool = False


class ContactUpdate(BaseModel):
    """Solo se cambian los campos enviados; un campo en null se borra."""

    model_config = ConfigDict(extra="forbid")

    client_site_id: uuid.UUID | None = None
    name: ContactName = None
    phone: Phone = None
    email: OptionalEmail = None
    receives_monthly_report: bool | None = None


class ContactAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    client_site_id: uuid.UUID | None
    name: str | None
    phone: str | None
    email: str | None
    receives_monthly_report: bool


class SiteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: SiteLabel = None
    address: Address
    reference: SiteReference = None


class SiteUpdate(BaseModel):
    """Solo se cambian los campos enviados; etiqueta o referencia en null se borran."""

    model_config = ConfigDict(extra="forbid")

    label: SiteLabel = None
    address: Address | None = None
    reference: SiteReference = None
    is_active: bool | None = None

    @field_validator("address", "is_active")
    @classmethod
    def _not_null(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("No puede quedar vacío.")
        return value


class SiteAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    label: str | None
    address: str
    reference: str | None
    is_active: bool

    @computed_field  # type: ignore[prop-decorator]
    @property
    def map_url(self) -> str:
        return site_map_url(self.address)


class ClientSiteTechnicianOut(BaseModel):
    """Lo que ve el técnico del domicilio de su orden. Sin datos de otros domicilios."""

    address: str
    reference: str | None
    map_url: str
    # Solo nombres: teléfono y email del contacto no llegan al técnico.
    contact_names: list[str]
