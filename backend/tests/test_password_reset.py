import uuid
from collections.abc import AsyncGenerator, Sequence

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.security import create_access_token, verify_password
from app.db.models.refresh_token import RefreshToken
from app.db.models.user import User, UserRole
from app.db.repositories.user import UserRepository
from app.db.session import SessionLocal, engine
from app.main import app
from tests.factories import make_user

TABLES = [User.__table__, RefreshToken.__table__]
COOKIE = "ot_refresh"
_AMBIGUOUS = set("0O1lI")


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


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _reload(user: User) -> User:
    async with SessionLocal() as session:
        reloaded = await UserRepository(session).get(user.id)
    assert reloaded is not None
    return reloaded


async def _reset(client: AsyncClient, admin: User, target: User) -> str:
    response = await client.post(f"/admin/users/{target.id}/password-reset", headers=_auth(admin))
    assert response.status_code == 200
    return str(response.json()["temporary_password"])


# Criterio 1: se genera una temporal legible, que se muestra una sola vez y sirve para entrar.
async def test_restablecer_genera_una_temporal_para_entrar(schema: None) -> None:
    admin = make_user(email="admin@ot-demo.com", role=UserRole.admin)
    tech = make_user(email="celu@ot-demo.com", role=UserRole.technician)
    await _seed([admin, tech])

    async with _client() as client:
        response = await client.post(f"/admin/users/{tech.id}/password-reset", headers=_auth(admin))
        temporal = response.json()["temporary_password"]
        vieja = await client.post(
            "/auth/login", json={"email": "celu@ot-demo.com", "password": "Secreta123"}
        )
        nueva = await client.post(
            "/auth/login", json={"email": "celu@ot-demo.com", "password": temporal}
        )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert len(temporal) == 12
    assert not _AMBIGUOUS & set(temporal)
    assert vieja.status_code == 401
    assert nueva.status_code == 200
    assert nueva.json()["user"]["must_change_password"] is True


# Criterio 1: después no se puede volver a ver (ninguna respuesta de usuarios la trae).
async def test_la_temporal_no_vuelve_a_aparecer(schema: None) -> None:
    admin = make_user(email="admin@ot-demo.com", role=UserRole.admin)
    tech = make_user(email="celu@ot-demo.com", role=UserRole.technician)
    await _seed([admin, tech])

    async with _client() as client:
        temporal = await _reset(client, admin, tech)
        uno = await client.get(f"/admin/users/{tech.id}", headers=_auth(admin))
        todos = await client.get("/admin/users", headers=_auth(admin))

    assert temporal not in uno.text
    assert temporal not in todos.text
    assert uno.json()["must_change_password"] is True


async def test_restablecer_un_usuario_inexistente_da_404(schema: None) -> None:
    admin = make_user(email="admin@ot-demo.com", role=UserRole.admin)
    await _seed([admin])

    async with _client() as client:
        response = await client.post(
            f"/admin/users/{uuid.uuid4()}/password-reset", headers=_auth(admin)
        )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "user_not_found"


# Criterio 2: se cierran todas las sesiones abiertas del usuario.
async def test_restablecer_cierra_las_sesiones_del_usuario(schema: None) -> None:
    admin = make_user(email="admin@ot-demo.com", role=UserRole.admin)
    tech = make_user(email="celu@ot-demo.com", role=UserRole.technician)
    await _seed([admin, tech])

    async with _client() as client:
        sesiones = []
        for _ in range(2):
            login = await client.post(
                "/auth/login", json={"email": "celu@ot-demo.com", "password": "Secreta123"}
            )
            sesiones.append(login.cookies[COOKIE])
        client.cookies.clear()
        await _reset(client, admin, tech)
        refrescos = [
            await client.post("/auth/refresh", headers={"Cookie": f"{COOKIE}={sesion}"})
            for sesion in sesiones
        ]

    assert [r.status_code for r in refrescos] == [401, 401]


# Criterio 3: con la temporal, la API niega todo salvo ver el perfil y cambiarla.
async def test_con_la_temporal_solo_se_puede_cambiar_la_contrasena(schema: None) -> None:
    admin = make_user(email="admin@ot-demo.com", role=UserRole.admin)
    otro = make_user(email="otro@ot-demo.com", role=UserRole.admin)
    await _seed([admin, otro])

    async with _client() as client:
        temporal = await _reset(client, admin, otro)
        login = await client.post(
            "/auth/login", json={"email": "otro@ot-demo.com", "password": temporal}
        )
        token = login.json()["access_token"]
        listar = await client.get("/admin/users", headers=_bearer(token))
        perfil = await client.get("/auth/me", headers=_bearer(token))
        sesion = login.cookies[COOKIE]
        client.cookies.clear()
        refresco = await client.post("/auth/refresh", headers={"Cookie": f"{COOKIE}={sesion}"})

    assert listar.status_code == 403
    assert listar.json()["detail"]["code"] == "password_change_required"
    assert perfil.status_code == 200
    assert perfil.json()["must_change_password"] is True
    assert refresco.status_code == 200
    assert refresco.json()["user"]["must_change_password"] is True


# Criterio 3: al cambiarla se libera el acceso.
async def test_cambiar_la_temporal_libera_el_acceso(schema: None) -> None:
    admin = make_user(email="admin@ot-demo.com", role=UserRole.admin)
    otro = make_user(email="otro@ot-demo.com", role=UserRole.admin)
    await _seed([admin, otro])

    async with _client() as client:
        temporal = await _reset(client, admin, otro)
        login = await client.post(
            "/auth/login", json={"email": "otro@ot-demo.com", "password": temporal}
        )
        token = login.json()["access_token"]
        cambio = await client.post(
            "/auth/password",
            json={"current_password": temporal, "new_password": "Nueva-clave-9"},
            headers=_bearer(token),
        )
        listar = await client.get("/admin/users", headers=_bearer(token))
        entrar = await client.post(
            "/auth/login", json={"email": "otro@ot-demo.com", "password": "Nueva-clave-9"}
        )

    assert cambio.status_code == 200
    assert cambio.json()["must_change_password"] is False
    assert listar.status_code == 200
    assert entrar.status_code == 200
    assert verify_password("Nueva-clave-9", (await _reload(otro)).password_hash)


# Criterio 4: menos de 8 caracteres o igual a la temporal no se guarda.
@pytest.mark.parametrize(
    ("nueva", "codigo"),
    [("corta", None), (None, "password_unchanged")],
)
async def test_la_nueva_contrasena_se_valida(
    schema: None, nueva: str | None, codigo: str | None
) -> None:
    admin = make_user(email="admin@ot-demo.com", role=UserRole.admin)
    tech = make_user(email="celu@ot-demo.com", role=UserRole.technician)
    await _seed([admin, tech])

    async with _client() as client:
        temporal = await _reset(client, admin, tech)
        cambio = await client.post(
            "/auth/password",
            json={"current_password": temporal, "new_password": nueva or temporal},
            headers=_auth(tech),
        )

    assert cambio.status_code == 422
    if codigo is not None:
        assert cambio.json()["detail"]["code"] == codigo
    assert (await _reload(tech)).must_change_password is True


async def test_cambiar_con_la_contrasena_actual_equivocada_se_rechaza(schema: None) -> None:
    tech = make_user(email="celu@ot-demo.com", role=UserRole.technician)
    await _seed([tech])

    async with _client() as client:
        cambio = await client.post(
            "/auth/password",
            json={"current_password": "otra-cosa-1", "new_password": "Nueva-clave-9"},
            headers=_auth(tech),
        )

    assert cambio.status_code == 422
    assert cambio.json()["detail"]["code"] == "invalid_current_password"
    assert verify_password("Secreta123", (await _reload(tech)).password_hash)


# Criterio 5: queda quién, sobre quién y cuándo; la temporal no queda en claro.
async def test_restablecer_queda_registrado_sin_la_contrasena_en_claro(schema: None) -> None:
    admin = make_user(email="admin@ot-demo.com", role=UserRole.admin)
    tech = make_user(email="celu@ot-demo.com", role=UserRole.technician)
    await _seed([admin, tech])

    async with _client() as client:
        temporal = await _reset(client, admin, tech)

    guardado = await _reload(tech)
    assert guardado.password_reset_by == admin.id
    assert guardado.password_reset_at is not None
    assert temporal not in guardado.password_hash
    assert verify_password(temporal, guardado.password_hash)


# Criterio 6: un técnico no puede restablecer contraseñas.
async def test_tecnico_no_puede_restablecer(schema: None) -> None:
    tech = make_user(email="celu@ot-demo.com", role=UserRole.technician)
    otro = make_user(email="otro@ot-demo.com", role=UserRole.technician)
    await _seed([tech, otro])

    async with _client() as client:
        response = await client.post(f"/admin/users/{otro.id}/password-reset", headers=_auth(tech))

    assert response.status_code == 403
    assert (await _reload(otro)).must_change_password is False
