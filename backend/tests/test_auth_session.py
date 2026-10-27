from collections.abc import AsyncGenerator, Sequence

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.db.models.refresh_token import RefreshToken
from app.db.models.user import User
from app.db.session import SessionLocal, engine
from app.main import app
from tests.factories import make_user

TABLES = [User.__table__, RefreshToken.__table__]
COOKIE = "ot_refresh"


@pytest.fixture
async def schema() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.create_all, tables=TABLES)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.drop_all, tables=list(reversed(TABLES)))
        await conn.execute(text("DROP TYPE IF EXISTS user_role"))


async def _seed(users: Sequence[User]) -> None:
    async with SessionLocal() as session:
        session.add_all(list(users))
        await session.commit()


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _login(client: AsyncClient, email: str, password: str = "Secreta123") -> str:
    """Ingresa y devuelve el refresh token, que llega solo en la cookie (E01-07)."""
    response = await client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.cookies[COOKIE]


def _with_cookie(value: str) -> dict[str, str]:
    # Se manda a mano: el navegador la envía solo a /api/auth, que el cliente de test no usa.
    return {"Cookie": f"{COOKIE}={value}"}


# Criterio 1: el token de refresco permite obtener un access token nuevo.
async def test_refresh_devuelve_nuevo_access_token(schema: None) -> None:
    await _seed([make_user(email="ana@ot-demo.com")])
    async with _client() as client:
        sesion = await _login(client, "ana@ot-demo.com")
        respuesta = await client.post("/auth/refresh", headers=_with_cookie(sesion))

    assert respuesta.status_code == 200
    assert respuesta.json()["access_token"]
    # La rotación entrega un refresh distinto al presentado.
    assert respuesta.cookies[COOKIE] != sesion


# Criterio 1 (rotación): el token de refresco viejo deja de servir tras usarse.
async def test_refresh_token_viejo_se_invalida_al_rotar(schema: None) -> None:
    await _seed([make_user(email="ana@ot-demo.com")])
    async with _client() as client:
        sesion = await _login(client, "ana@ot-demo.com")
        primera = await client.post("/auth/refresh", headers=_with_cookie(sesion))
        assert primera.status_code == 200

        reuso = await client.post("/auth/refresh", headers=_with_cookie(sesion))

    assert reuso.status_code == 401


# Criterio 2: al cerrar sesión, el token de refresco se invalida.
async def test_logout_invalida_el_refresh_token(schema: None) -> None:
    await _seed([make_user(email="ana@ot-demo.com")])
    async with _client() as client:
        sesion = await _login(client, "ana@ot-demo.com")

        logout = await client.post("/auth/logout", headers=_with_cookie(sesion))
        assert logout.status_code == 204

        despues = await client.post("/auth/refresh", headers=_with_cookie(sesion))

    assert despues.status_code == 401


# Criterio 4: si el usuario queda inactivo, su sesión deja de renovarse.
async def test_usuario_inactivo_no_puede_refrescar(schema: None) -> None:
    user = make_user(email="ana@ot-demo.com")
    await _seed([user])
    async with _client() as client:
        sesion = await _login(client, "ana@ot-demo.com")

        # Se da de baja al usuario (borrado lógico).
        async with SessionLocal() as db:
            encontrado = await db.get(User, user.id)
            assert encontrado is not None
            encontrado.is_active = False
            await db.commit()

        respuesta = await client.post("/auth/refresh", headers=_with_cookie(sesion))

    assert respuesta.status_code == 401


# Un token de refresco inventado no sirve.
async def test_refresh_token_invalido_devuelve_401(schema: None) -> None:
    await _seed([make_user(email="ana@ot-demo.com")])
    async with _client() as client:
        respuesta = await client.post("/auth/refresh", headers=_with_cookie("no-existe"))
    assert respuesta.status_code == 401
