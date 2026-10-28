import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TimestampedBase
from app.domain.work_order import SignaturePurpose


class Signature(TimestampedBase):
    """Firma del cliente en pantalla (E05-07). La imagen va al bucket, nunca a la base.

    En el cierre no se pide DNI (D-008): solo el nombre de quien firma.
    """

    __tablename__ = "signature"

    closure_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_order_closure.id"), nullable=False, index=True
    )
    purpose: Mapped[SignaturePurpose] = mapped_column(
        Enum(SignaturePurpose, name="signature_purpose"), nullable=False
    )
    # Dato personal: no se loguea.
    signer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    image_file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stored_file.id"), unique=True, nullable=False
    )
    signed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
