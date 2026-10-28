from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status

from app.api.deps import SessionDep, require_role
from app.api.schemas.auth import (
    LoginRequest,
    PasswordChange,
    RefreshResponse,
    TokenResponse,
    UserOut,
)
from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.models.user import User, UserRole
from app.services import auth as auth_service
from app.services import session as session_service
from app.services.auth import authenticate

router = APIRouter(prefix="/auth", tags=["acceso"])

# El propio perfil lo puede ver cualquier rol autenticado, incluso con una
# contraseña temporal: así los clientes saben que tienen que pedir cambiarla (E01-05).
AnyRole = Annotated[
    User,
    Depends(
        require_role(
            UserRole.admin,
            UserRole.technician,
            UserRole.owner,
            allow_temporary_password=True,
        )
    ),
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
    return TokenResponse(access_token=access, user=UserOut.model_validate(user))


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    session: SessionDep,
    response: Response,
    cookie_token: RefreshCookie = None,
) -> RefreshResponse:
    try:
        if cookie_token is None:
            raise session_service.InvalidRefreshTokenError
        access, new_refresh, user = await session_service.rotate_refresh_token(
            session, cookie_token
        )
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
    return RefreshResponse(access_token=access, user=UserOut.model_validate(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    session: SessionDep,
    response: Response,
    cookie_token: RefreshCookie = None,
) -> None:
    if cookie_token is not None:
        await session_service.revoke_refresh_token(session, cookie_token)
    _clear_refresh_cookie(response)


@router.get("/me", response_model=UserOut)
async def me(current_user: AnyRole) -> User:
    """Devuelve el usuario autenticado."""
    return current_user


@router.post("/password", response_model=UserOut)
async def change_password(
    payload: PasswordChange, session: SessionDep, current_user: AnyRole
) -> User:
    """Cambia la contraseña propia; con una temporal, es lo único que se puede hacer."""
    try:
        return await auth_service.change_password(
            session, current_user, payload.current_password, payload.new_password
        )
    except auth_service.InvalidCurrentPasswordError:
        raise _password_error(
            "invalid_current_password", "La contraseña actual no es correcta."
        ) from None
    except auth_service.PasswordUnchangedError:
        raise _password_error(
            "password_unchanged", "La contraseña nueva tiene que ser distinta de la actual."
        ) from None


def _password_error(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={"code": code, "message": message},
    )
