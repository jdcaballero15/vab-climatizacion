from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status

from app.api.deps import SessionDep, require_role
from app.api.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RefreshResponse,
    TokenResponse,
    UserOut,
)
from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.models.user import User, UserRole
from app.services import session as session_service
from app.services.auth import authenticate

router = APIRouter(prefix="/auth", tags=["acceso"])

# El propio perfil lo puede ver cualquier rol autenticado.
AnyRole = Annotated[
    User, Depends(require_role(UserRole.admin, UserRole.technician, UserRole.owner))
]

# Cookie httpOnly con el refresh token (ADR 0010, E01-07).
REFRESH_COOKIE = "ot_refresh"
RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE)]


def _set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=settings.refresh_token_expire_days * 86400,
        path=settings.refresh_cookie_path,
        secure=settings.refresh_cookie_secure,
        httponly=True,
        samesite="strict",
    )


def _clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        REFRESH_COOKIE,
        path=settings.refresh_cookie_path,
        secure=settings.refresh_cookie_secure,
        httponly=True,
        samesite="strict",
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: SessionDep, response: Response) -> TokenResponse:
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
    _set_refresh_cookie(response, refresh)
    return TokenResponse(
        access_token=access, refresh_token=refresh, user=UserOut.model_validate(user)
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    session: SessionDep,
    response: Response,
    cookie_token: RefreshCookie = None,
    payload: RefreshRequest | None = None,
) -> RefreshResponse:
    raw = cookie_token or (payload.refresh_token if payload else None)
    try:
        if raw is None:
            raise session_service.InvalidRefreshTokenError
        access, new_refresh, user = await session_service.rotate_refresh_token(session, raw)
    except session_service.InvalidRefreshTokenError:
        # La excepción descarta los headers de `response`: el borrado va en la propia 401.
        clear = Response()
        _clear_refresh_cookie(clear)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_refresh_token", "message": "Sesión no válida o expirada."},
            headers={"set-cookie": clear.headers["set-cookie"]},
        ) from None
    _set_refresh_cookie(response, new_refresh)
    return RefreshResponse(
        access_token=access, refresh_token=new_refresh, user=UserOut.model_validate(user)
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    session: SessionDep,
    response: Response,
    cookie_token: RefreshCookie = None,
    payload: LogoutRequest | None = None,
) -> None:
    raw = cookie_token or (payload.refresh_token if payload else None)
    if raw is not None:
        await session_service.revoke_refresh_token(session, raw)
    _clear_refresh_cookie(response)


@router.get("/me", response_model=UserOut)
async def me(current_user: AnyRole) -> User:
    """Devuelve el usuario autenticado."""
    return current_user
