import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.models.user import User, UserRole
from app.db.repositories.user import UserRepository
from app.db.session import get_session

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_bearer = HTTPBearer(auto_error=False)

_NOT_AUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"code": "not_authenticated", "message": "Sesión no válida o expirada."},
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    """Carga el usuario del JWT. 401 si falta, es inválido o está inactivo."""
    if credentials is None:
        raise _NOT_AUTHENTICATED

    try:
        claims = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(claims["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError) as error:
        raise _NOT_AUTHENTICATED from error

    user = await UserRepository(session).get(user_id)
    if user is None or not user.is_active:
        raise _NOT_AUTHENTICATED

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: UserRole) -> Callable[[User], Awaitable[User]]:
    """Dependencia que exige que el usuario tenga uno de los roles dados (403 si no)."""

    async def dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "forbidden", "message": "No tenés permiso para esta acción."},
            )
        return user

    # Marca para el test de contrato de rutas (criterio 5): toda ruta protegida
    # declara explícitamente sus roles con esta dependencia.
    dependency.required_roles = roles  # type: ignore[attr-defined]
    return dependency
