from datetime import datetime

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TimestampedBase


class LoginFailure(TimestampedBase):
    """Un intento de inicio de sesión fallido (E01-06). Al entrar bien o al levantar el
    bloqueo se dan de baja los de esa cuenta (borrado lógico)."""

    __tablename__ = "login_failure"
    __table_args__ = (
        Index("ix_login_failure_email_at", "email", "occurred_at"),
        Index("ix_login_failure_ip_at", "ip", "occurred_at"),
    )

    # En minúsculas, como se busca el usuario. No se loguea.
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    ip: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
