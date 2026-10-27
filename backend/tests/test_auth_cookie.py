"""E01-07: el refresh token viaja en una cookie httpOnly (ADR 0010)."""

from collections.abc import AsyncGenerator, Sequence
from http.cookies import SimpleCookie

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import text

from app.core.config import get_settings
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
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://test")


def _set_cookie(response: Response) -> SimpleCookie:
    """La cookie que manda la respuesta, con sus atributos."""
    cookie: SimpleCookie = SimpleCookie()
    for header in response.headers.get_list("set-cookie"):
        cookie.load(header)
    assert COOKIE in cookie, "la respuesta no manda la cookie de sesión"
    return cookie


def _with_cookie(value: str) -> dict[str, str]:
    # Se manda a mano: el navegador la envía solo a /api/auth, que el cliente de test no usa.
    return {"Cookie": f"{COOKIE}={value}"}


async def _login(client: AsyncClient, email: str = "ana@ot-demo.com") -> Response:
    response = await client.post("/auth/login", json={"email": email, "password": "Secreta123"})
    assert response.status_code == 200
    return response


# Criterios 5 y 6: la cookie no la lee un script ni viaja desde otro sitio.
async def test_login_manda_la_cookie_httponly_secure_y_strict(schema: None) -> None:
    await _seed([make_user(email="ana@ot-demo.com")])
    async with _client() as client:
        response = await _login(client)

    morsel = _set_cookie(response)[COOKIE]
    assert morsel.value
    assert morsel["httponly"]
    assert morsel["secure"]
    assert morsel["samesite"].lower() == "strict"
    assert morsel["path"] == "/api/auth"
    assert int(morsel["max-age"]) == get_settings().refresh_token_expire_days * 86400


# Criterio 1: con la cookie sola se recupera la sesión, con el usuario.
async def test_refresh_con_la_cookie_devuelve_access_token_y_usuario(schema: None) -> None:
    await _seed([make_user(email="ana@ot-demo.com")])
    async with _client() as client:
        token = _set_cookie(await _login(client))[COOKIE].value
        response = await client.post("/auth/refresh", headers=_with_cookie(token))

    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["user"]["email"] == "ana@ot-demo.com"
    # La renovación rota el token y manda la cookie nueva.
    assert _set_cookie(response)[COOKIE].value not in ("", token)


# Criterio 2: un token ya usado no sirve, y la respuesta borra la cookie.
async def test_refresh_con_cookie_ya_usada_da_401_y_la_borra(schema: None) -> None:
    await _seed([make_user(email="ana@ot-demo.com")])
    async with _client() as client:
        token = _set_cookie(await _login(client))[COOKIE].value
        primera = await client.post("/auth/refresh", headers=_with_cookie(token))
        assert primera.status_code == 200
        reuso = await client.post("/auth/refresh", headers=_with_cookie(token))

    assert reuso.status_code == 401
    assert reuso.json()["detail"]["code"] == "invalid_refresh_token"
    assert _set_cookie(reuso)[COOKIE]["max-age"] == "0"


# Criterio 2: sin cookie ni cuerpo, no hay sesión.
async def test_refresh_sin_cookie_ni_cuerpo_da_401(schema: None) -> None:
    async with _client() as client:
        response = await client.post("/auth/refresh")

    assert response.status_code == 401


# Criterio 3: cerrar sesión revoca el token de la cookie y la borra.
async def test_logout_con_la_cookie_la_revoca_y_la_borra(schema: None) -> None:
    await _seed([make_user(email="ana@ot-demo.com")])
    async with _client() as client:
        token = _set_cookie(await _login(client))[COOKIE].value
        logout = await client.post("/auth/logout", headers=_with_cookie(token))
        despues = await client.post("/auth/refresh", headers=_with_cookie(token))

    assert logout.status_code == 204
    assert _set_cookie(logout)[COOKIE]["max-age"] == "0"
    assert despues.status_code == 401


# Criterio 3: cerrar sesión sin cookie igual responde bien (idempotente).
async def test_logout_sin_cookie_responde_204(schema: None) -> None:
    async with _client() as client:
        response = await client.post("/auth/logout")

    assert response.status_code == 204


# Criterio 4: la cookie de un usuario dado de baja no sirve.
async def test_cookie_de_usuario_dado_de_baja_da_401(schema: None) -> None:
    user = make_user(email="ana@ot-demo.com")
    await _seed([user])
    async with _client() as client:
        token = _set_cookie(await _login(client))[COOKIE].value
        async with SessionLocal() as db:
            encontrado = await db.get(User, user.id)
            assert encontrado is not None
            encontrado.is_active = False
            await db.commit()
        response = await client.post("/auth/refresh", headers=_with_cookie(token))

    assert response.status_code == 401


# Criterio 5: el refresh token no aparece en ninguna respuesta de la API.
async def test_login_y_refresh_no_devuelven_el_refresh_token(schema: None) -> None:
    await _seed([make_user(email="ana@ot-demo.com")])
    async with _client() as client:
        login = await _login(client)
        token = _set_cookie(login)[COOKIE].value
        refresh = await client.post("/auth/refresh", headers=_with_cookie(token))

    assert refresh.status_code == 200
    for response in (login, refresh):
        assert "refresh_token" not in response.json()
        assert token not in response.text


# Criterio 5: el token en el cuerpo ya no se acepta; solo cuenta la cookie.
async def test_refresh_y_logout_ignoran_el_token_en_el_cuerpo(schema: None) -> None:
    await _seed([make_user(email="ana@ot-demo.com")])
    async with _client() as client:
        token = _set_cookie(await _login(client))[COOKIE].value
        por_cuerpo = await client.post("/auth/refresh", json={"refresh_token": token})
        await client.post("/auth/logout", json={"refresh_token": token})
        # El logout por cuerpo no lo revocó: con la cookie todavía sirve.
        con_cookie = await client.post("/auth/refresh", headers=_with_cookie(token))

    assert por_cuerpo.status_code == 401
    assert con_cookie.status_code == 200
