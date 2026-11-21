from collections.abc import AsyncGenerator, Sequence

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.security import create_access_token
from app.db.models.login_failure import LoginFailure
from app.db.models.refresh_token import RefreshToken
from app.db.models.user import User, UserRole
from app.db.repositories.user import UserRepository
from app.db.session import SessionLocal, engine
from app.main import app
from tests.factories import make_user


@pytest.fixture
async def schema() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(
            User.metadata.create_all,
            tables=[User.__table__, RefreshToken.__table__, LoginFailure.__table__],
        )
    yield
    async with engine.begin() as conn:
        await conn.run_sync(
            User.metadata.drop_all,
            tables=[LoginFailure.__table__, RefreshToken.__table__, User.__table__],
        )
        await conn.execute(text("DROP TYPE IF EXISTS user_role"))


async def _seed(users: Sequence[User]) -> None:
    async with SessionLocal() as session:
        session.add_all(list(users))
        await session.commit()


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _nuevo_usuario(email: str = "nuevo@ot-demo.com") -> dict[str, str]:
    return {
        "full_name": "Usuario Nuevo",
        "email": email,
        "role": "technician",
        "password": "Secreta123",
    }


# Criterio 1: administración crea un usuario y este puede iniciar sesión.
async def test_crear_usuario_permite_iniciar_sesion(schema: None) -> None:
    admin = make_user(email="admin@ot-demo.com", role=UserRole.admin)
    await _seed([admin])

    async with _client() as client:
        creado = await client.post("/admin/users", json=_nuevo_usuario(), headers=_auth(admin))
        assert creado.status_code == 201
        assert creado.json()["email"] == "nuevo@ot-demo.com"

        login = await client.post(
            "/auth/login", json={"email": "nuevo@ot-demo.com", "password": "Secreta123"}
        )
    assert login.status_code == 200


# Criterio 2: un correo ya registrado se rechaza con un mensaje claro.
async def test_correo_duplicado_se_rechaza(schema: None) -> None:
    admin = make_user(email="admin@ot-demo.com", role=UserRole.admin)
    await _seed([admin])

    async with _client() as client:
        primero = await client.post("/admin/users", json=_nuevo_usuario(), headers=_auth(admin))
        assert primero.status_code == 201
        repetido = await client.post("/admin/users", json=_nuevo_usuario(), headers=_auth(admin))

    assert repetido.status_code == 409
    assert repetido.json()["detail"]["code"] == "email_already_exists"


# Criterio 3: dar de baja deja al usuario inactivo (borrado lógico), sin poder iniciar sesión.
async def test_baja_de_usuario_es_logica_y_bloquea_el_login(schema: None) -> None:
    admin = make_user(email="admin@ot-demo.com", role=UserRole.admin)
    await _seed([admin])

    async with _client() as client:
        creado = await client.post("/admin/users", json=_nuevo_usuario(), headers=_auth(admin))
        user_id = creado.json()["id"]

        baja = await client.delete(f"/admin/users/{user_id}", headers=_auth(admin))
        assert baja.status_code == 204

        login = await client.post(
            "/auth/login", json={"email": "nuevo@ot-demo.com", "password": "Secreta123"}
        )
        assert login.status_code == 401

    # La fila se conserva (borrado lógico), con deleted_at marcado.
    async with SessionLocal() as session:
        dado_de_baja = await UserRepository(session).get_by_email(
            "nuevo@ot-demo.com", include_deleted=True
        )
    assert dado_de_baja is not None
    assert dado_de_baja.deleted_at is not None
    assert dado_de_baja.is_active is False


# Criterio 5: un técnico no puede gestionar usuarios (403).
async def test_tecnico_no_puede_gestionar_usuarios(schema: None) -> None:
    tech = make_user(email="tec@ot-demo.com", role=UserRole.technician)
    await _seed([tech])

    async with _client() as client:
        listar = await client.get("/admin/users", headers=_auth(tech))
        crear = await client.post("/admin/users", json=_nuevo_usuario(), headers=_auth(tech))

    assert listar.status_code == 403
    assert crear.status_code == 403


# La lista sale ordenada por nombre: restablecer o editar a alguien no lo mueve de lugar.
async def test_listado_ordenado_por_nombre_aunque_se_modifique_uno(schema: None) -> None:
    admin = make_user(email="admin@ot-demo.com", full_name="carla Admin")
    beto = make_user(email="beto@ot-demo.com", full_name="Beto Ficticio")
    ana = make_user(email="ana@ot-demo.com", full_name="Ana Ficticia")
    await _seed([admin, beto, ana])

    async with _client() as client:
        reset = await client.post(f"/admin/users/{ana.id}/password-reset", headers=_auth(admin))
        assert reset.status_code == 200
        listar = await client.get("/admin/users", headers=_auth(admin))

    assert [user["full_name"] for user in listar.json()] == [
        "Ana Ficticia",
        "Beto Ficticio",
        "carla Admin",
    ]


async def _dar_de_baja(client: AsyncClient, admin: User) -> str:
    creado = await client.post("/admin/users", json=_nuevo_usuario(), headers=_auth(admin))
    user_id: str = creado.json()["id"]
    baja = await client.delete(f"/admin/users/{user_id}", headers=_auth(admin))
    assert baja.status_code == 204
    return user_id


# E01-08, criterio 1: los dados de baja se listan aparte, no en la lista de activos.
async def test_dados_de_baja_se_listan_aparte(schema: None) -> None:
    admin = make_user(email="admin@ot-demo.com", role=UserRole.admin)
    await _seed([admin])

    async with _client() as client:
        user_id = await _dar_de_baja(client, admin)
        activos = await client.get("/admin/users", headers=_auth(admin))
        bajas = await client.get("/admin/users/deactivated", headers=_auth(admin))

    assert [user["id"] for user in activos.json()] == [str(admin.id)]
    assert bajas.status_code == 200
    assert [user["id"] for user in bajas.json()] == [user_id]
    assert bajas.json()[0]["is_active"] is False
    assert bajas.json()[0]["deleted_at"] is not None


# E01-08, criterio 2: reactivar lo devuelve a la lista y entra con la contraseña que tenía.
async def test_reactivar_usuario_vuelve_a_permitir_el_login(schema: None) -> None:
    admin = make_user(email="admin@ot-demo.com", role=UserRole.admin)
    await _seed([admin])

    async with _client() as client:
        user_id = await _dar_de_baja(client, admin)

        reactivado = await client.post(f"/admin/users/{user_id}/reactivate", headers=_auth(admin))
        assert reactivado.status_code == 200
        assert reactivado.json()["is_active"] is True
        assert reactivado.json()["deleted_at"] is None

        activos = await client.get("/admin/users", headers=_auth(admin))
        bajas = await client.get("/admin/users/deactivated", headers=_auth(admin))
        login = await client.post(
            "/auth/login", json={"email": "nuevo@ot-demo.com", "password": "Secreta123"}
        )

    assert user_id in [user["id"] for user in activos.json()]
    assert bajas.json() == []
    assert login.status_code == 200


# E01-08, criterio 3: reactivar a alguien activo no cambia nada; un id que no existe da 404.
async def test_reactivar_activo_o_inexistente(schema: None) -> None:
    admin = make_user(email="admin@ot-demo.com", role=UserRole.admin)
    await _seed([admin])

    async with _client() as client:
        activo = await client.post(f"/admin/users/{admin.id}/reactivate", headers=_auth(admin))
        inexistente = await client.post(
            "/admin/users/00000000-0000-0000-0000-000000000000/reactivate", headers=_auth(admin)
        )

    assert activo.status_code == 200
    assert activo.json()["is_active"] is True
    assert inexistente.status_code == 404


# E01-08, criterio 4: el técnico no ve los dados de baja ni puede reactivar (403).
async def test_tecnico_no_puede_reactivar(schema: None) -> None:
    tech = make_user(email="tec@ot-demo.com", role=UserRole.technician)
    await _seed([tech])

    async with _client() as client:
        bajas = await client.get("/admin/users/deactivated", headers=_auth(tech))
        reactivar = await client.post(f"/admin/users/{tech.id}/reactivate", headers=_auth(tech))

    assert bajas.status_code == 403
    assert reactivar.status_code == 403
