import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TimestampedBase


class AuditEvent(TimestampedBase):
    """Un cambio relevante sobre una entidad: quién, cuándo y qué (E12-02, base de E12-01).

    entity y action son texto libre corto ("client", "deactivated"): sumar una entidad no
    obliga a migrar. Las órdenes tienen su propia línea de tiempo (work_order_event).
    """

    __tablename__ = "audit_event"

    entity: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
