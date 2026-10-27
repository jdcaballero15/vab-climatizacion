import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TimestampedBase


class LegacyReference(TimestampedBase):
    """Identificador de un registro en el sistema anterior (Persat), por entidad importada.

    Hace la importación repetible: lo que ya tiene referencia no se vuelve a crear.
    """

    __tablename__ = "legacy_reference"
    __table_args__ = (
        UniqueConstraint("entity", "source", "legacy_id", name="uq_legacy_reference_entity_id"),
    )

    entity: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="persat")
    legacy_id: Mapped[str] = mapped_column(String(255), nullable=False)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
