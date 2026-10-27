import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TimestampedBase


class StoredFile(TimestampedBase):
    """Un archivo del bucket (E00-09). La base guarda solo la referencia, nunca el contenido.

    Se crea al pedir la subida; queda disponible para usarse recién con confirmed_at.
    """

    __tablename__ = "stored_file"

    # Para qué se subió (por ejemplo "closure_photo"); decide los tipos permitidos.
    purpose: Mapped[str] = mapped_column(String(50), nullable=False)
    object_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("app_user.id"), nullable=False, index=True
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
