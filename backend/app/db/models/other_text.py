from sqlalchemy import Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TimestampedBase


class DismissedOtherText(TimestampedBase):
    """Un texto de "Otro" que administración descartó (E02-07): deja de mostrarse en la
    revisión, pero sigue en las órdenes que lo tienen."""

    __tablename__ = "dismissed_other_text"
    __table_args__ = (
        Index(
            "uq_dismissed_other_text",
            "kind",
            "text_key",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    # failure, repair o part.
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    # El texto normalizado (minúsculas y espacios simples): agrupa variantes simples.
    text_key: Mapped[str] = mapped_column(String(255), nullable=False)
