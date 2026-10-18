from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep, require_role
from app.api.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.core.security import create_access_token
from app.db.models.user import User, UserRole
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

    token = create_access_token(subject=str(user.id), role=user.role.value)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(current_user: AnyRole) -> User:
    """Devuelve el usuario autenticado."""
    return current_user
