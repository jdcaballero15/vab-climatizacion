"""Freno a los intentos de adivinar contraseñas (E01-06).

Cinco fallos seguidos de una cuenta en diez minutos la bloquean quince minutos; desde una
misma dirección IP el tope es más alto. Umbrales en la configuración. Al entrar bien, o si
administración levanta el bloqueo, se dan de baja los fallos de esa cuenta.
"""

import logging
import math
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models.login_failure import LoginFailure
from app.db.models.user import User

logger = logging.getLogger("app.auth")


class AccountLockedError(Exception):
    code = "account_locked"

    def __init__(self, minutes: int) -> None:
        unit = "minuto" if minutes == 1 else "minutos"
        self.message = (
            f"Demasiados intentos fallidos. Probá de nuevo en {minutes} {unit} "
            "o pedile a administración que desbloquee la cuenta."
        )
        super().__init__(self.message)


class TooManyAttemptsError(Exception):
    code = "too_many_attempts"
    message = "Demasiados intentos fallidos desde esta conexión. Esperá unos minutos."


def _normalize(email: str) -> str:
    return email.strip().lower()


async def locked_until(session: AsyncSession, email: str) -> datetime | None:
    """Hasta cuándo está bloqueada la cuenta; None si no lo está."""
    settings = get_settings()
    now = datetime.now(UTC)
    window = now - timedelta(minutes=settings.login_failure_window_minutes)
    times = (
        await session.scalars(
            select(LoginFailure.occurred_at)
            .where(
                LoginFailure.email == _normalize(email),
                LoginFailure.deleted_at.is_(None),
                LoginFailure.occurred_at >= window - timedelta(minutes=settings.login_lock_minutes),
            )
            .order_by(LoginFailure.occurred_at)
        )
    ).all()
    # Hay bloqueo si alguna racha de N fallos entró en la ventana y no venció.
    n = settings.login_max_failures
    for index in range(len(times) - n + 1):
        first, last = times[index], times[index + n - 1]
        if last - first <= timedelta(minutes=settings.login_failure_window_minutes):
            until = times[-1] + timedelta(minutes=settings.login_lock_minutes)
            if until > now:
                return until
    return None


async def check(session: AsyncSession, email: str, ip: str) -> None:
    settings = get_settings()
    until = await locked_until(session, email)
    if until is not None:
        minutes = max(1, math.ceil((until - datetime.now(UTC)).total_seconds() / 60))
        raise AccountLockedError(minutes)
    window = datetime.now(UTC) - timedelta(minutes=settings.login_failure_window_minutes)
    from_ip = await session.scalar(
        select(func.count()).where(
            LoginFailure.ip == ip,
            LoginFailure.deleted_at.is_(None),
            LoginFailure.occurred_at >= window,
        )
    )
    if (from_ip or 0) >= settings.login_ip_max_failures:
        raise TooManyAttemptsError


async def record_failure(
    session: AsyncSession, email: str, ip: str, user_id: uuid.UUID | None
) -> None:
    session.add(LoginFailure(email=_normalize(email), ip=ip))
    await session.commit()
    if await locked_until(session, email) is not None:
        # Registro del bloqueo (criterio 2), sin el correo: solo el id si la cuenta existe.
        logger.warning("Cuenta bloqueada por intentos fallidos (usuario %s)", user_id or "-")


async def clear(session: AsyncSession, email: str) -> None:
    """Da de baja los fallos de la cuenta: al entrar bien o al desbloquear."""
    await session.execute(
        update(LoginFailure)
        .where(LoginFailure.email == _normalize(email), LoginFailure.deleted_at.is_(None))
        .values(deleted_at=datetime.now(UTC))
    )


async def unlock(session: AsyncSession, user: User) -> None:
    await clear(session, user.email)
    await session.commit()
    logger.info("Bloqueo levantado por administración (usuario %s)", user.id)
