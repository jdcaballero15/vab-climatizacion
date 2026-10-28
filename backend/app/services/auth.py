from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password, waste_password_time
from app.db.models.user import User
from app.db.repositories.user import UserRepository


class InvalidCurrentPasswordError(Exception):
    """La contraseña actual no coincide."""


class PasswordUnchangedError(Exception):
    """La nueva contraseña es igual a la actual (por ejemplo, la temporal)."""


async def authenticate(session: AsyncSession, email: str, password: str) -> User | None:
    """Devuelve el usuario si las credenciales son válidas y está activo, o None.

    No distingue entre correo inexistente, usuario inactivo y contraseña
    incorrecta: siempre None, para no revelar si el correo existe.
    """
    user = await UserRepository(session).get_by_email(email)

    if user is None or not user.is_active:
        waste_password_time()
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


async def change_password(
    session: AsyncSession, user: User, current_password: str, new_password: str
) -> User:
    """Cambia la contraseña propia y libera el acceso si era temporal (E01-05)."""
    if not verify_password(current_password, user.password_hash):
        raise InvalidCurrentPasswordError
    if new_password == current_password:
        raise PasswordUnchangedError
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    await session.commit()
    await session.refresh(user)
    return user
