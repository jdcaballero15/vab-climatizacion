from collections.abc import AsyncGenerator, Sequence

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.config import get_settings
from app.db.models.login_failure import LoginFailure
from app.db.models.user import User, UserRole
from app.db.session import SessionLocal, engine
from app.main import app
from tests.factories import make_user


@pytest.fixture
async def schema() -> AsyncGenerator[None, None]:
    from app.db.models.refresh_token import RefreshToken

    tables = [User.__table__, RefreshToken.__table__, LoginFailure.__table__]
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
    # El refresh token va solo en la cookie (E01-07, criterio 5).
    assert "refresh_token" not in body
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


# E01-06: cinco fallos seguidos bloquean la cuenta; el mensaje dice cuánto esperar y
# administración la puede desbloquear. Entrar bien borra los fallos.
async def test_bloqueo_por_intentos_fallidos(schema: None) -> None:
    ana = make_user(email="ana@ot-demo.com", password="Secreta123", role=UserRole.admin)
    jefe = make_user(email="jefe@ot-demo.com", password="Secreta123", role=UserRole.owner)
    await _seed([ana, jefe])
    mala = {"email": "ana@ot-demo.com", "password": "Equivocada1"}
    buena = {"email": "ana@ot-demo.com", "password": "Secreta123"}

    async with _client() as client:
        fallos = [await client.post("/auth/login", json=mala) for _ in range(5)]
        bloqueada = await client.post("/auth/login", json=buena)
        login_jefe = await client.post(
            "/auth/login", json={"email": "jefe@ot-demo.com", "password": "Secreta123"}
        )
        token = login_jefe.json()["access_token"]
        usuarios = await client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})
        desbloqueo = await client.post(
            f"/admin/users/{ana.id}/unlock", headers={"Authorization": f"Bearer {token}"}
        )
        despues = await client.post("/auth/login", json=buena)

    assert [r.status_code for r in fallos] == [401] * 5
    assert bloqueada.status_code == 429
    assert bloqueada.json()["detail"]["code"] == "account_locked"
    assert "15 minutos" in bloqueada.json()["detail"]["message"]
    por_correo = {u["email"]: u["locked_until"] for u in usuarios.json()}
    assert por_correo["ana@ot-demo.com"] is not None
    assert por_correo["jefe@ot-demo.com"] is None
    assert desbloqueo.json()["locked_until"] is None
    assert despues.status_code == 200


async def test_cuatro_fallos_y_un_acierto_no_bloquean(schema: None) -> None:
    await _seed([make_user(email="ana@ot-demo.com", password="Secreta123")])
    mala = {"email": "ana@ot-demo.com", "password": "Equivocada1"}
    buena = {"email": "ana@ot-demo.com", "password": "Secreta123"}

    async with _client() as client:
        for _ in range(4):
            await client.post("/auth/login", json=mala)
        primero = await client.post("/auth/login", json=buena)
        for _ in range(4):
            await client.post("/auth/login", json=mala)
        segundo = await client.post("/auth/login", json=buena)

    assert (primero.status_code, segundo.status_code) == (200, 200)


# Un correo que no existe también suma fallos: no revela si la cuenta existe.
async def test_correo_inexistente_tambien_se_bloquea(schema: None) -> None:
    mala = {"email": "nadie@ot-demo.com", "password": "Equivocada1"}

    async with _client() as client:
        respuestas = [await client.post("/auth/login", json=mala) for _ in range(6)]

    assert [r.status_code for r in respuestas] == [401] * 5 + [429]
