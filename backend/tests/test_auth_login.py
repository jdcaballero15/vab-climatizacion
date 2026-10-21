from collections.abc import AsyncGenerator, Sequence

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.config import get_settings
from app.db.models.user import User, UserRole
from app.db.session import SessionLocal, engine
from app.main import app
from tests.factories import make_user


@pytest.fixture
async def schema() -> AsyncGenerator[None, None]:
    from app.db.models.refresh_token import RefreshToken

    tables = [User.__table__, RefreshToken.__table__]
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.create_all, tables=tables)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.drop_all, tables=list(reversed(tables)))
        await conn.execute(text("DROP TYPE IF EXISTS user_role"))


async def _seed(users: Sequence[User]) -> None:
    async with SessionLocal() as session:
        session.add_all(list(users))
        await session.commit()


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# Criterio 1: usuario activo + credenciales correctas -> recibe sesión y su rol.
async def test_login_ok_devuelve_token_y_rol(schema: None) -> None:
    await _seed([make_user(email="ana@ot-demo.com", password="Secreta123", role=UserRole.admin)])

    async with _client() as client:
        response = await client.post(
            "/auth/login", json={"email": "ana@ot-demo.com", "password": "Secreta123"}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["refresh_token"]
    assert body["user"]["email"] == "ana@ot-demo.com"
    assert body["user"]["role"] == "admin"
    assert "password_hash" not in body["user"]

    settings = get_settings()
    claims = jwt.decode(
        body["access_token"], settings.app_secret_key, algorithms=[settings.jwt_algorithm]
    )
    assert claims["role"] == "admin"
    assert claims["sub"] == body["user"]["id"]


# Criterio 2: credenciales incorrectas -> mensaje genérico que no revela si el correo existe.
async def test_login_credenciales_incorrectas_mensaje_generico(schema: None) -> None:
    await _seed([make_user(email="ana@ot-demo.com", password="Secreta123")])

    async with _client() as client:
        mala_contrasena = await client.post(
            "/auth/login", json={"email": "ana@ot-demo.com", "password": "incorrecta"}
        )
        correo_inexistente = await client.post(
            "/auth/login", json={"email": "nadie@ot-demo.com", "password": "incorrecta"}
        )

    assert mala_contrasena.status_code == 401
    assert correo_inexistente.status_code == 401
    # Misma respuesta: no se puede deducir si el correo existe.
    assert mala_contrasena.json() == correo_inexistente.json()


# Criterio 3: un usuario dado de baja no puede iniciar sesión.
async def test_login_usuario_inactivo_rechazado(schema: None) -> None:
    await _seed([make_user(email="baja@ot-demo.com", password="Secreta123", is_active=False)])

    async with _client() as client:
        response = await client.post(
            "/auth/login", json={"email": "baja@ot-demo.com", "password": "Secreta123"}
        )

    assert response.status_code == 401


# Criterio 4: la contraseña se almacena con Argon2, nunca en texto plano.
async def test_password_se_guarda_con_argon2(schema: None) -> None:
    usuario = make_user(email="hash@ot-demo.com", password="Secreta123")

    assert usuario.password_hash != "Secreta123"
    assert usuario.password_hash.startswith("$argon2")
