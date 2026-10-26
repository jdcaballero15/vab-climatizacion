import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import get_settings

_hasher = PasswordHasher()

# Hash de descarte con el mismo coste, para que verificar un usuario inexistente
# tarde lo mismo que uno real y no se filtre por tiempo si el correo existe.
_DUMMY_HASH = _hasher.hash("dummy-password-para-tiempo-constante")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def waste_password_time() -> None:
    """Verifica contra un hash de descarte para igualar el tiempo de respuesta."""
    verify_password("", _DUMMY_HASH)


def create_access_token(*, subject: str, role: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.access_token_expire_minutes)).timestamp()),
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Valida y decodifica el JWT. Lanza jwt.InvalidTokenError si no es válido."""
    settings = get_settings()
    return jwt.decode(token, settings.app_secret_key, algorithms=[settings.jwt_algorithm])


def generate_refresh_token() -> str:
    """Genera un token de refresco aleatorio (se entrega al cliente una sola vez)."""
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    """Hash del token de refresco. En la base solo se guarda el hash, nunca el valor."""
    return hashlib.sha256(token.encode()).hexdigest()
