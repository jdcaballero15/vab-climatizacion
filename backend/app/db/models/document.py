import uuid
from enum import StrEnum

from sqlalchemy import Enum, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TimestampedBase


class DocumentKind(StrEnum):
    pickup_receipt = "pickup_receipt"
    delivery_receipt = "delivery_receipt"


class OrderDocument(TimestampedBase):
    """Comprobante PDF de una orden, guardado en el bucket (E09-01, E09-02). Uno por orden y
    tipo: pedirlo de nuevo devuelve el mismo archivo (criterio 3)."""

    __tablename__ = "order_document"
    __table_args__ = (
        Index(
            "uq_order_document_kind",
            "work_order_id",
            "kind",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    work_order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("work_order.id"), nullable=False)
    kind: Mapped[DocumentKind] = mapped_column(
        Enum(DocumentKind, name="document_kind"), nullable=False
    )
    file_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stored_file.id"), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), nullable=False)
