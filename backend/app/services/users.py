import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.user import UserCreate, UserUpdate
from app.core.security import generate_temporary_password, hash_password
from app.db.models.user import User, UserRole
from app.db.repositories.refresh_token import RefreshTokenRepository
from app.db.repositories.user import UserRepository


class EmailAlreadyExistsError(Exception):
    """El correo ya pertenece a otro usuario (activo o dado de baja)."""


class UserNotFoundError(Exception):
    """No existe un usuario activo con ese id."""


class AdminAlreadyExistsError(Exception):
    """Ya hay un administrador: los demás usuarios se crean desde la administración."""


async def create_user(session: AsyncSession, data: UserCreate) -> User:
    repo = UserRepository(session)
    # El correo es único a nivel de base, incluso para usuarios dados de baja.
    if await repo.get_by_email(str(data.email), include_deleted=True) is not None:
        raise EmailAlreadyExistsError

    user = User(
        full_name=data.full_name,
        email=str(data.email),
        role=data.role,
        password_hash=hash_password(data.password),
        is_active=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def create_first_admin(session: AsyncSession, data: UserCreate) -> User:
    """Primer administrador de una instalación nueva, para poder entrar a crear los demás."""
    users = await UserRepository(session).list()
    if any(user.role == UserRole.admin for user in users):
        raise AdminAlreadyExistsError
    return await create_user(session, data.model_copy(update={"role": UserRole.admin}))


async def list_users(session: AsyncSession) -> Sequence[User]:
    return await UserRepository(session).list_by_name()


async def get_user(session: AsyncSession, user_id: uuid.UUID) -> User:
    user = await UserRepository(session).get(user_id)
    if user is None:
        raise UserNotFoundError
    return user


async def update_user(session: AsyncSession, user_id: uuid.UUID, data: UserUpdate) -> User:
    user = await get_user(session, user_id)
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.role is not None:
        user.role = data.role
    await session.commit()
    await session.refresh(user)
    return user


async def deactivate_user(session: AsyncSession, user_id: uuid.UUID) -> None:
    """Da de baja (borrado lógico): queda inactivo y no puede iniciar sesión.

    Conserva la fila y su historial. Cuando existan las órdenes (E04) habrá que
    avisar y pedir reasignación si el técnico tiene órdenes abiertas (criterio 4).
    """
    user = await get_user(session, user_id)
    user.deleted_at = datetime.now(UTC)
    user.is_active = False
    await session.commit()


async def reset_password(session: AsyncSession, user_id: uuid.UUID, actor: User) -> str:
    """Pone una contraseña temporal, cierra las sesiones del usuario y la devuelve (E01-05).

    La temporal solo vive en esta respuesta: en la base queda el hash.
    """
    user = await get_user(session, user_id)
    temporary = generate_temporary_password()
    now = datetime.now(UTC)
    user.password_hash = hash_password(temporary)
    user.must_change_password = True
    user.password_reset_at = now
    user.password_reset_by = actor.id
    await RefreshTokenRepository(session).revoke_all_for_user(user.id, now)
    await session.commit()
    return temporary
