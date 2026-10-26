from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep, require_role
from app.api.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RefreshResponse,
    TokenResponse,
    UserOut,
)
from app.core.security import create_access_token
from app.db.models.user import User, UserRole
from app.services import session as session_service
from app.services.auth import authenticate

router = APIRouter(prefix="/auth", tags=["acceso"])

# El propio perfil lo puede ver cualquier rol autenticado.
AnyRole = Annotated[
    User, Depends(require_role(UserRole.admin, UserRole.technician, UserRole.owner))
]


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: SessionDep) -> TokenResponse:
    user = await authenticate(session, payload.email, payload.password)
    if user is None:
        # Mensaje genérico: no revela si el correo existe.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "invalid_credentials",
                "message": "Correo o contraseña incorrectos.",
            },
        )

    access = create_access_token(subject=str(user.id), role=user.role.value)
    refresh = await session_service.issue_refresh_token(session, user)
    await session.commit()
    return TokenResponse(
        access_token=access, refresh_token=refresh, user=UserOut.model_validate(user)
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(payload: RefreshRequest, session: SessionDep) -> RefreshResponse:
    try:
        access, new_refresh = await session_service.rotate_refresh_token(
            session, payload.refresh_token
        )
    except session_service.InvalidRefreshTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_refresh_token", "message": "Sesión no válida o expirada."},
        ) from None
    return RefreshResponse(access_token=access, refresh_token=new_refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: LogoutRequest, session: SessionDep) -> None:
    await session_service.revoke_refresh_token(session, payload.refresh_token)


@router.get("/me", response_model=UserOut)
async def me(current_user: AnyRole) -> User:
    """Devuelve el usuario autenticado."""
    return current_user
