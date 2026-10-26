import uuid
from enum import StrEnum

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TimestampedBase


class ClientSegment(StrEnum):
    private_person = "private_person"
    business = "business"
    government = "government"
    healthcare = "healthcare"
    hotel = "hotel"
    unclassified = "unclassified"


class TaxCondition(StrEnum):
    final_consumer = "final_consumer"
    registered_taxpayer = "registered_taxpayer"
    monotributo = "monotributo"


class Client(TimestampedBase):
    """Cliente de la empresa. CUIT o DNI es dato personal (ver SECURITY.md)."""

    __tablename__ = "client"

    # Texto porque Persat mezcla series (numérica y CLI-). Forma parte del código de los
    # equipos (D-002), por eso es único también contra los dados de baja y no se edita.
    number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    segment: Mapped[ClientSegment] = mapped_column(
        Enum(ClientSegment, name="client_segment"),
        nullable=False,
        default=ClientSegment.unclassified,
    )
    tax_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    tax_condition: Mapped[TaxCondition | None] = mapped_column(
        Enum(TaxCondition, name="tax_condition"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ClientSite(TimestampedBase):
    """Domicilio o sede de un cliente: a dónde va el técnico y dónde están los equipos."""

    __tablename__ = "client_site"

    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("client.id"), nullable=False, index=True
    )
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Incluye la localidad; el enlace al mapa suma la provincia.
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ClientContact(TimestampedBase):
    """Persona de contacto de un cliente. Teléfono y email son datos personales."""

    __tablename__ = "client_contact"

    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("client.id"), nullable=False, index=True
    )
    # Sin domicilio, el contacto es del cliente en general.
    client_site_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("client_site.id"), nullable=True, index=True
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    receives_monthly_report: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
