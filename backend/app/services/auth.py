from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password, waste_password_time
from app.db.models.user import User
from app.db.repositories.user import UserRepository


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
