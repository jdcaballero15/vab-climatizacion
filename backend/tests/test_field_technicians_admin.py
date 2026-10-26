import uuid
from collections.abc import AsyncGenerator, Sequence

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import text

from app.core.security import create_access_token
from app.db.models.crew import Crew, FieldTechnician
from app.db.models.user import User, UserRole
from app.db.session import SessionLocal, engine
from app.main import app
from tests.factories import make_user

# E02-09: técnicos, personas de campo sin usuario que se tildan al cerrar (D-013).

TABLES = [User.__table__, Crew.__table__, FieldTechnician.__table__]
URL = "/admin/field-technicians"


@pytest.fixture
async def schema() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.create_all, tables=TABLES)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.drop_all, tables=list(reversed(TABLES)))
        await conn.execute(text("DROP TYPE IF EXISTS user_role"))


@pytest.fixture
async def admin(schema: None) -> User:
    user = make_user(email="admin@ot-demo.com", role=UserRole.admin)
    await _seed([user])
    return user


async def _seed(items: Sequence[object]) -> None:
    async with SessionLocal() as session:
        session.add_all(list(items))
        await session.commit()


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _crear(client: AsyncClient, admin: User, nombre: str) -> dict[str, object]:
    response = await client.post(URL, json={"full_name": nombre}, headers=_auth(admin))
    assert response.status_code == 201, response.text
    body: dict[str, object] = response.json()
    return body


def _nombres(response: Response) -> list[str]:
    assert response.status_code == 200, response.text
    return [item["full_name"] for item in response.json()]


def _code(response: Response) -> str:
    code: str = response.json()["detail"]["code"]
    return code


# Criterio 5: un técnico nuevo queda activo, sin usuario.
async def test_crear_tecnico_queda_activo(admin: User) -> None:
    async with _client() as client:
        creado = await _crear(client, admin, "  Diego   Ficticio ")
        listado = await client.get(URL, headers=_auth(admin))

    assert creado["full_name"] == "Diego Ficticio"
    assert creado["is_active"] is True
    assert set(creado) == {"id", "full_name", "is_active"}
    assert _nombres(listado) == ["Diego Ficticio"]


async def test_renombrar_tecnico(admin: User) -> None:
    async with _client() as client:
        creado = await _crear(client, admin, "Diego Ficticio")
        renombrado = await client.patch(
            f"{URL}/{creado['id']}", json={"full_name": "Diego Ficticio (h)"}, headers=_auth(admin)
        )

    assert renombrado.json()["full_name"] == "Diego Ficticio (h)"


# Decisión del plan: nombres repetidos se rechazan, también contra los inactivos.
async def test_nombre_repetido_se_rechaza(admin: User) -> None:
    async with _client() as client:
        creado = await _crear(client, admin, "Diego Ficticio")
        await client.patch(f"{URL}/{creado['id']}", json={"is_active": False}, headers=_auth(admin))
        repetido = await client.post(
            URL, json={"full_name": "diego  ficticio"}, headers=_auth(admin)
        )

    assert repetido.status_code == 409
    assert _code(repetido) == "field_technician_name_already_exists"


# Criterio 6: desactivar lo saca de la lista para tildar.
async def test_desactivar_tecnico(admin: User) -> None:
    async with _client() as client:
        creado = await _crear(client, admin, "Diego Ficticio")
        await client.patch(f"{URL}/{creado['id']}", json={"is_active": False}, headers=_auth(admin))
        activos = await client.get(URL, headers=_auth(admin))
        todos = await client.get(f"{URL}?include_inactive=true", headers=_auth(admin))

    assert _nombres(activos) == []
    assert _nombres(todos) == ["Diego Ficticio"]


# Criterio 7: primero los activos, por nombre.
async def test_listado_activos_primero_por_nombre(admin: User) -> None:
    async with _client() as client:
        for nombre in ("Zoe Ficticia", "Ana Ficticia", "Lucas Ficticio"):
            await _crear(client, admin, nombre)
        listado = await client.get(URL, headers=_auth(admin))
        ana = listado.json()[0]
        await client.patch(f"{URL}/{ana['id']}", json={"is_active": False}, headers=_auth(admin))
        todos = await client.get(f"{URL}?include_inactive=true", headers=_auth(admin))

    assert _nombres(listado) == ["Ana Ficticia", "Lucas Ficticio", "Zoe Ficticia"]
    assert _nombres(todos) == ["Lucas Ficticio", "Zoe Ficticia", "Ana Ficticia"]


async def test_tecnico_inexistente(admin: User) -> None:
    async with _client() as client:
        response = await client.patch(
            f"{URL}/{uuid.uuid4()}", json={"full_name": "X"}, headers=_auth(admin)
        )

    assert response.status_code == 404
    assert _code(response) == "field_technician_not_found"


# Criterio 8: técnico (usuario de escuadrilla) y dirección reciben 403.
@pytest.mark.parametrize("rol", [UserRole.technician, UserRole.owner])
async def test_tecnico_y_direccion_no_gestionan_tecnicos(schema: None, rol: UserRole) -> None:
    usuario = make_user(email=f"{rol.value}@ot-demo.com", role=rol)
    await _seed([usuario])

    async with _client() as client:
        listar = await client.get(URL, headers=_auth(usuario))
        crear = await client.post(URL, json={"full_name": "Diego"}, headers=_auth(usuario))

    assert listar.status_code == 403
    assert crear.status_code == 403
