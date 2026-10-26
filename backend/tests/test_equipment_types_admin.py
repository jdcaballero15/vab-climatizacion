from collections.abc import AsyncGenerator, Sequence

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import text

from app.core.security import create_access_token
from app.db.models.catalog import EquipmentType
from app.db.models.user import User, UserRole
from app.db.session import SessionLocal, engine
from app.main import app
from tests.factories import make_user

TABLES = [User.__table__, EquipmentType.__table__]
URL = "/admin/equipment-types"


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


async def _seed(users: Sequence[User]) -> None:
    async with SessionLocal() as session:
        session.add_all(list(users))
        await session.commit()


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _crear_tipo(client: AsyncClient, admin: User, name: str) -> dict[str, object]:
    response = await client.post(URL, json={"name": name}, headers=_auth(admin))
    assert response.status_code == 201, response.text
    body: dict[str, object] = response.json()
    return body


def _nombres(response: Response) -> list[str]:
    assert response.status_code == 200, response.text
    return [item["name"] for item in response.json()]


# Criterio 1: crear un tipo de equipo lo deja activo y en el listado de activos.
async def test_crear_tipo_queda_activo_y_listado(admin: User) -> None:
    async with _client() as client:
        creado = await _crear_tipo(client, admin, "Split")
        listado = await client.get(URL, headers=_auth(admin))

    assert creado["is_active"] is True
    assert _nombres(listado) == ["Split"]


# Criterio 2: renombrar se ve en todo lugar que lo referencia por id.
async def test_renombrar_tipo_se_ve_por_id(admin: User) -> None:
    async with _client() as client:
        tipo = await _crear_tipo(client, admin, "Heladera")
        renombrado = await client.patch(
            f"{URL}/{tipo['id']}", json={"name": "Heladera comercial"}, headers=_auth(admin)
        )
        consultado = await client.get(f"{URL}/{tipo['id']}", headers=_auth(admin))

    assert renombrado.status_code == 200
    assert consultado.json()["name"] == "Heladera comercial"


async def test_tipo_inexistente_devuelve_404(admin: User) -> None:
    async with _client() as client:
        consultado = await client.get(
            f"{URL}/00000000-0000-0000-0000-000000000000", headers=_auth(admin)
        )
        editado = await client.patch(
            f"{URL}/00000000-0000-0000-0000-000000000000",
            json={"is_active": False},
            headers=_auth(admin),
        )
    for response in (consultado, editado):
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "equipment_type_not_found"


# Criterio 3: desactivar saca de los activos, se consulta por id y se reactiva.
async def test_desactivar_y_reactivar_tipo(admin: User) -> None:
    async with _client() as client:
        tipo = await _crear_tipo(client, admin, "Cámara frigorífica")
        url = f"{URL}/{tipo['id']}"

        await client.patch(url, json={"is_active": False}, headers=_auth(admin))
        activos = await client.get(URL, headers=_auth(admin))
        todos = await client.get(f"{URL}?include_inactive=true", headers=_auth(admin))
        consultado = await client.get(url, headers=_auth(admin))

        await client.patch(url, json={"is_active": True}, headers=_auth(admin))
        reactivado = await client.get(URL, headers=_auth(admin))

    assert _nombres(activos) == []
    assert _nombres(todos) == ["Cámara frigorífica"]
    assert consultado.json() == {"id": tipo["id"], "name": "Cámara frigorífica", "is_active": False}
    assert _nombres(reactivado) == ["Cámara frigorífica"]


# Criterio 4: nombre duplicado sin distinguir mayúsculas ni espacios, también contra inactivos.
@pytest.mark.parametrize(
    "duplicado", ["Aire central", "aire central", "  AIRE CENTRAL  ", "Aire    central"]
)
async def test_nombre_duplicado_se_rechaza(admin: User, duplicado: str) -> None:
    async with _client() as client:
        await _crear_tipo(client, admin, "Aire central")
        response = await client.post(URL, json={"name": duplicado}, headers=_auth(admin))
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "equipment_type_name_already_exists"


async def test_nombre_duplicado_contra_tipo_inactivo_se_rechaza(admin: User) -> None:
    async with _client() as client:
        tipo = await _crear_tipo(client, admin, "Split")
        await client.patch(f"{URL}/{tipo['id']}", json={"is_active": False}, headers=_auth(admin))
        response = await client.post(URL, json={"name": "split"}, headers=_auth(admin))
    assert response.status_code == 409


async def test_renombrar_a_un_nombre_existente_se_rechaza(admin: User) -> None:
    async with _client() as client:
        await _crear_tipo(client, admin, "Cámara frigorífica")
        tipo = await _crear_tipo(client, admin, "Split")
        response = await client.patch(
            f"{URL}/{tipo['id']}", json={"name": "CÁMARA FRIGORÍFICA"}, headers=_auth(admin)
        )
    assert response.status_code == 409


async def test_renombrar_cambiando_solo_mayusculas_se_acepta(admin: User) -> None:
    async with _client() as client:
        tipo = await _crear_tipo(client, admin, "split")
        response = await client.patch(
            f"{URL}/{tipo['id']}", json={"name": "Split"}, headers=_auth(admin)
        )
    assert response.status_code == 200
    assert response.json()["name"] == "Split"


async def test_los_acentos_distinguen_nombres(admin: User) -> None:
    async with _client() as client:
        await _crear_tipo(client, admin, "Cámara frigorífica")
        response = await client.post(URL, json={"name": "Camara frigorifica"}, headers=_auth(admin))
    assert response.status_code == 201


async def test_el_nombre_se_guarda_sin_espacios_sobrantes(admin: User) -> None:
    async with _client() as client:
        creado = await _crear_tipo(client, admin, "  Heladera   comercial  ")
    assert creado["name"] == "Heladera comercial"


# Criterio 5: un nombre vacío o de solo espacios se rechaza con 422.
@pytest.mark.parametrize("vacio", ["", "   "])
async def test_nombre_vacio_se_rechaza(admin: User, vacio: str) -> None:
    async with _client() as client:
        tipo = await _crear_tipo(client, admin, "Split")
        crear = await client.post(URL, json={"name": vacio}, headers=_auth(admin))
        renombrar = await client.patch(
            f"{URL}/{tipo['id']}", json={"name": vacio}, headers=_auth(admin)
        )
    assert crear.status_code == 422
    assert renombrar.status_code == 422


# Criterio 7: técnico y dirección reciben 403 en todo el catálogo, también al leer.
@pytest.mark.parametrize("role", [UserRole.technician, UserRole.owner])
async def test_tecnico_y_direccion_reciben_403(admin: User, role: UserRole) -> None:
    otro = make_user(email="otro@ot-demo.com", role=role)
    await _seed([otro])
    async with _client() as client:
        tipo = await _crear_tipo(client, admin, "Split")
        tipo_url = f"{URL}/{tipo['id']}"
        respuestas = [
            await client.get(URL, headers=_auth(otro)),
            await client.post(URL, json={"name": "X"}, headers=_auth(otro)),
            await client.get(tipo_url, headers=_auth(otro)),
            await client.patch(tipo_url, json={"name": "X"}, headers=_auth(otro)),
            await client.patch(tipo_url, json={"is_active": False}, headers=_auth(otro)),
        ]
    assert [r.status_code for r in respuestas] == [403] * len(respuestas)
