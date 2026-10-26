from collections.abc import AsyncGenerator, Sequence

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import text

from app.core.security import create_access_token
from app.db.models.catalog import Task, WorkType
from app.db.models.user import User, UserRole
from app.db.session import SessionLocal, engine
from app.main import app
from tests.factories import make_user

TABLES = [User.__table__, WorkType.__table__, Task.__table__]


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
    response = await client.post("/admin/work-types", json={"name": name}, headers=_auth(admin))
    assert response.status_code == 201, response.text
    body: dict[str, object] = response.json()
    return body


async def _crear_tarea(
    client: AsyncClient, admin: User, work_type_id: object, name: str
) -> Response:
    return await client.post(
        f"/admin/work-types/{work_type_id}/tasks", json={"name": name}, headers=_auth(admin)
    )


def _nombres(response: Response) -> list[str]:
    assert response.status_code == 200, response.text
    return [item["name"] for item in response.json()]


# Criterio 1: crear un tipo de trabajo lo deja activo y en el listado de activos.
async def test_crear_tipo_queda_activo_y_listado(admin: User) -> None:
    async with _client() as client:
        creado = await _crear_tipo(client, admin, "Instalación")
        listado = await client.get("/admin/work-types", headers=_auth(admin))

    assert creado["is_active"] is True
    assert _nombres(listado) == ["Instalación"]


# Criterio 2: renombrar se ve en todo lugar que lo referencia por id.
async def test_renombrar_tipo_se_ve_por_id(admin: User) -> None:
    async with _client() as client:
        tipo = await _crear_tipo(client, admin, "Service")
        renombrado = await client.patch(
            f"/admin/work-types/{tipo['id']}", json={"name": "Mantenimiento"}, headers=_auth(admin)
        )
        consultado = await client.get(f"/admin/work-types/{tipo['id']}", headers=_auth(admin))

    assert renombrado.status_code == 200
    assert consultado.json()["name"] == "Mantenimiento"


async def test_tipo_inexistente_devuelve_404(admin: User) -> None:
    async with _client() as client:
        response = await client.get(
            "/admin/work-types/00000000-0000-0000-0000-000000000000", headers=_auth(admin)
        )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "work_type_not_found"


# Criterio 3: agregar, renombrar y desactivar subtareas se refleja en las activas.
async def test_subtareas_agregar_renombrar_y_desactivar(admin: User) -> None:
    async with _client() as client:
        tipo = await _crear_tipo(client, admin, "Reparación")
        carga = await _crear_tarea(client, admin, tipo["id"], "Carga de gas")
        limpieza = await _crear_tarea(client, admin, tipo["id"], "Limpieza de filtros")
        assert carga.status_code == 201
        assert limpieza.status_code == 201

        await client.patch(
            f"/admin/work-types/{tipo['id']}/tasks/{carga.json()['id']}",
            json={"name": "Carga de refrigerante"},
            headers=_auth(admin),
        )
        await client.patch(
            f"/admin/work-types/{tipo['id']}/tasks/{limpieza.json()['id']}",
            json={"is_active": False},
            headers=_auth(admin),
        )
        activas = await client.get(f"/admin/work-types/{tipo['id']}/tasks", headers=_auth(admin))

    assert _nombres(activas) == ["Carga de refrigerante"]


# Criterio 4: desactivar saca de los activos, se consulta por id y se reactiva.
async def test_desactivar_y_reactivar_tipo(admin: User) -> None:
    async with _client() as client:
        tipo = await _crear_tipo(client, admin, "Retiro")
        url = f"/admin/work-types/{tipo['id']}"

        await client.patch(url, json={"is_active": False}, headers=_auth(admin))
        activos = await client.get("/admin/work-types", headers=_auth(admin))
        todos = await client.get("/admin/work-types?include_inactive=true", headers=_auth(admin))
        consultado = await client.get(url, headers=_auth(admin))

        await client.patch(url, json={"is_active": True}, headers=_auth(admin))
        reactivado = await client.get("/admin/work-types", headers=_auth(admin))

    assert _nombres(activos) == []
    assert _nombres(todos) == ["Retiro"]
    assert consultado.json() == {"id": tipo["id"], "name": "Retiro", "is_active": False}
    assert _nombres(reactivado) == ["Retiro"]


async def test_desactivar_y_reactivar_subtarea(admin: User) -> None:
    async with _client() as client:
        tipo = await _crear_tipo(client, admin, "Relevamiento")
        tarea = await _crear_tarea(client, admin, tipo["id"], "Medición")
        url = f"/admin/work-types/{tipo['id']}/tasks"
        tarea_url = f"{url}/{tarea.json()['id']}"

        await client.patch(tarea_url, json={"is_active": False}, headers=_auth(admin))
        activas = await client.get(url, headers=_auth(admin))
        todas = await client.get(f"{url}?include_inactive=true", headers=_auth(admin))
        await client.patch(tarea_url, json={"is_active": True}, headers=_auth(admin))
        reactivadas = await client.get(url, headers=_auth(admin))

    assert _nombres(activas) == []
    assert _nombres(todas) == ["Medición"]
    assert _nombres(reactivadas) == ["Medición"]


async def test_subtarea_de_otro_tipo_devuelve_404(admin: User) -> None:
    async with _client() as client:
        tipo = await _crear_tipo(client, admin, "Instalación")
        otro = await _crear_tipo(client, admin, "Retiro")
        tarea = await _crear_tarea(client, admin, tipo["id"], "Montaje")
        response = await client.patch(
            f"/admin/work-types/{otro['id']}/tasks/{tarea.json()['id']}",
            json={"name": "Otra"},
            headers=_auth(admin),
        )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "task_not_found"


# Criterio 5: un tipo desactivado no ofrece subtareas, aunque cada una conserve su estado.
async def test_tipo_desactivado_no_ofrece_subtareas(admin: User) -> None:
    async with _client() as client:
        tipo = await _crear_tipo(client, admin, "Devolución")
        await _crear_tarea(client, admin, tipo["id"], "Entrega")
        await client.patch(
            f"/admin/work-types/{tipo['id']}", json={"is_active": False}, headers=_auth(admin)
        )
        url = f"/admin/work-types/{tipo['id']}/tasks"
        activas = await client.get(url, headers=_auth(admin))
        todas = await client.get(f"{url}?include_inactive=true", headers=_auth(admin))

    assert _nombres(activas) == []
    assert todas.json()[0]["is_active"] is True


# Criterio 6: nombre duplicado sin distinguir mayúsculas ni espacios, también contra inactivos.
@pytest.mark.parametrize(
    "duplicado",
    ["Puesta en marcha", "puesta en marcha", "  PUESTA EN MARCHA  ", "Puesta   en marcha"],
)
async def test_nombre_duplicado_de_tipo_se_rechaza(admin: User, duplicado: str) -> None:
    async with _client() as client:
        await _crear_tipo(client, admin, "Puesta en marcha")
        response = await client.post(
            "/admin/work-types", json={"name": duplicado}, headers=_auth(admin)
        )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "work_type_name_already_exists"


async def test_nombre_duplicado_contra_tipo_inactivo_se_rechaza(admin: User) -> None:
    async with _client() as client:
        tipo = await _crear_tipo(client, admin, "Retiro")
        await client.patch(
            f"/admin/work-types/{tipo['id']}", json={"is_active": False}, headers=_auth(admin)
        )
        response = await client.post(
            "/admin/work-types", json={"name": "retiro"}, headers=_auth(admin)
        )
    assert response.status_code == 409


async def test_renombrar_a_un_nombre_existente_se_rechaza(admin: User) -> None:
    async with _client() as client:
        await _crear_tipo(client, admin, "Instalación")
        tipo = await _crear_tipo(client, admin, "Reparación")
        response = await client.patch(
            f"/admin/work-types/{tipo['id']}", json={"name": "INSTALACIÓN"}, headers=_auth(admin)
        )
    assert response.status_code == 409


async def test_renombrar_cambiando_solo_mayusculas_se_acepta(admin: User) -> None:
    async with _client() as client:
        tipo = await _crear_tipo(client, admin, "service")
        response = await client.patch(
            f"/admin/work-types/{tipo['id']}", json={"name": "Service"}, headers=_auth(admin)
        )
    assert response.status_code == 200
    assert response.json()["name"] == "Service"


async def test_los_acentos_distinguen_nombres(admin: User) -> None:
    async with _client() as client:
        await _crear_tipo(client, admin, "Instalación")
        response = await client.post(
            "/admin/work-types", json={"name": "Instalacion"}, headers=_auth(admin)
        )
    assert response.status_code == 201


async def test_el_nombre_se_guarda_sin_espacios_sobrantes(admin: User) -> None:
    async with _client() as client:
        creado = await _crear_tipo(client, admin, "  Carga   de gas  ")
    assert creado["name"] == "Carga de gas"


# Criterio 7: subtareas únicas dentro de su tipo; el mismo nombre en otro tipo se acepta.
async def test_subtarea_duplicada_en_el_mismo_tipo_se_rechaza(admin: User) -> None:
    async with _client() as client:
        tipo = await _crear_tipo(client, admin, "Reparación")
        await _crear_tarea(client, admin, tipo["id"], "Carga de gas")
        response = await _crear_tarea(client, admin, tipo["id"], " carga  DE gas ")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "task_name_already_exists"


async def test_mismo_nombre_de_subtarea_en_otro_tipo_se_acepta(admin: User) -> None:
    async with _client() as client:
        reparacion = await _crear_tipo(client, admin, "Reparación")
        service = await _crear_tipo(client, admin, "Service")
        await _crear_tarea(client, admin, reparacion["id"], "Limpieza")
        response = await _crear_tarea(client, admin, service["id"], "Limpieza")
    assert response.status_code == 201


# Criterio 8: un nombre vacío o de solo espacios se rechaza con 422.
@pytest.mark.parametrize("vacio", ["", "   "])
async def test_nombre_vacio_se_rechaza(admin: User, vacio: str) -> None:
    async with _client() as client:
        tipo = await _crear_tipo(client, admin, "Retiro")
        crear_tipo = await client.post(
            "/admin/work-types", json={"name": vacio}, headers=_auth(admin)
        )
        renombrar = await client.patch(
            f"/admin/work-types/{tipo['id']}", json={"name": vacio}, headers=_auth(admin)
        )
        crear_tarea = await _crear_tarea(client, admin, tipo["id"], vacio)
    assert crear_tipo.status_code == 422
    assert renombrar.status_code == 422
    assert crear_tarea.status_code == 422


# Criterio 10: técnico y dirección reciben 403 en todo el catálogo.
@pytest.mark.parametrize("role", [UserRole.technician, UserRole.owner])
async def test_tecnico_y_direccion_reciben_403(admin: User, role: UserRole) -> None:
    otro = make_user(email="otro@ot-demo.com", role=role)
    await _seed([otro])
    async with _client() as client:
        tipo = await _crear_tipo(client, admin, "Retiro")
        tipo_url = f"/admin/work-types/{tipo['id']}"
        tarea = await _crear_tarea(client, admin, tipo["id"], "Traslado")
        tarea_url = f"{tipo_url}/tasks/{tarea.json()['id']}"
        respuestas = [
            await client.get("/admin/work-types", headers=_auth(otro)),
            await client.post("/admin/work-types", json={"name": "X"}, headers=_auth(otro)),
            await client.get(tipo_url, headers=_auth(otro)),
            await client.patch(tipo_url, json={"is_active": False}, headers=_auth(otro)),
            await client.get(f"{tipo_url}/tasks", headers=_auth(otro)),
            await client.post(f"{tipo_url}/tasks", json={"name": "X"}, headers=_auth(otro)),
            await client.patch(tarea_url, json={"name": "X"}, headers=_auth(otro)),
        ]
    assert [r.status_code for r in respuestas] == [403] * len(respuestas)
