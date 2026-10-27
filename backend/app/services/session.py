from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
)
from app.db.models.refresh_token import RefreshToken
from app.db.models.user import User
from app.db.repositories.refresh_token import RefreshTokenRepository
from app.db.repositories.user import UserRepository


class InvalidRefreshTokenError(Exception):
    """El token de refresco no existe, está revocado o venció."""


async def issue_refresh_token(session: AsyncSession, user: User) -> str:
    """Crea un token de refresco para el usuario y devuelve el valor en claro."""
    settings = get_settings()
    raw = generate_refresh_token()
    token = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(raw),
        expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days),
    )
    session.add(token)
    return raw


async def rotate_refresh_token(session: AsyncSession, raw_token: str) -> tuple[str, str, User]:
    """Valida y rota el token de refresco. Devuelve (access, nuevo refresh, usuario).

    Revoca el token presentado y emite uno nuevo. Falla si el token no es válido
    o si el usuario ya no está activo (criterio 4: las sesiones dejan de andar).
    """
    repo = RefreshTokenRepository(session)
    stored = await repo.get_by_hash(hash_refresh_token(raw_token))

    now = datetime.now(UTC)
    if stored is None or stored.revoked_at is not None or stored.expires_at <= now:
        raise InvalidRefreshTokenError

    user = await UserRepository(session).get(stored.user_id)
    if user is None or not user.is_active:
        raise InvalidRefreshTokenError

    stored.revoked_at = now
    new_raw = await issue_refresh_token(session, user)
    await session.commit()

    access = create_access_token(subject=str(user.id), role=user.role.value)
    return access, new_raw, user


async def revoke_refresh_token(session: AsyncSession, raw_token: str) -> None:
    """Invalida el token de refresco (cierre de sesión). Idempotente."""
    repo = RefreshTokenRepository(session)
    stored = await repo.get_by_hash(hash_refresh_token(raw_token))
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = datetime.now(UTC)
        await session.commit()
