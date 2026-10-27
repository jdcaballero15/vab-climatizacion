import uuid

from pydantic import BaseModel, ConfigDict, EmailStr

from app.db.models.user import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole


# El refresh token no va en ninguna respuesta: solo en la cookie httpOnly (E01-07, criterio 5).
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 (tipo de token OAuth, no es un secreto)
    user: UserOut


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 (tipo de token OAuth, no es un secreto)
    user: UserOut
