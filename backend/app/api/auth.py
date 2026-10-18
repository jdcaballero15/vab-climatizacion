from fastapi import APIRouter, HTTPException, status

from app.api.deps import SessionDep
from app.api.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.core.security import create_access_token
from app.services.auth import authenticate

router = APIRouter(prefix="/auth", tags=["acceso"])


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
