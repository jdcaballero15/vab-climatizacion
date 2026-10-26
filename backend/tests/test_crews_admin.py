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

# E02-09: escuadrillas (lista fija con nombre y el usuario de su celular, D-013).

TABLES = [User.__table__, Crew.__table__, FieldTechnician.__table__]
URL = "/admin/crews"


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


@pytest.fixture
async def celular(schema: None) -> User:
    user = make_user(email="celular1@ot-demo.com", role=UserRole.technician, full_name="Celular 1")
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


async def _crear(client: AsyncClient, admin: User, **payload: object) -> dict[str, object]:
    response = await client.post(URL, json=payload, headers=_auth(admin))
    assert response.status_code == 201, response.text
    body: dict[str, object] = response.json()
    return body


def _code(response: Response) -> str:
    code: str = response.json()["detail"]["code"]
    return code


def _nombres(response: Response) -> list[str]:
    assert response.status_code == 200, response.text
    return [item["name"] for item in response.json()]


# Criterio 1: una escuadrilla nueva queda activa.
async def test_crear_escuadrilla_queda_activa(admin: User) -> None:
    async with _client() as client:
        creada = await _crear(client, admin, name="  Escuadrilla   1 ")
        listado = await client.get(URL, headers=_auth(admin))

    assert creada["name"] == "Escuadrilla 1"
    assert creada["is_active"] is True
    assert creada["app_user"] is None
    assert _nombres(listado) == ["Escuadrilla 1"]


# Criterio 2: el usuario del celular es un técnico activo y libre.
async def test_asociar_usuario_del_celular(admin: User, celular: User) -> None:
    async with _client() as client:
        creada = await _crear(client, admin, name="Escuadrilla 1", app_user_id=str(celular.id))

    assert creada["app_user"] == {
        "id": str(celular.id),
        "full_name": "Celular 1",
        "email": "celular1@ot-demo.com",
        "is_active": True,
    }


async def test_asociar_y_desasociar_al_editar(admin: User, celular: User) -> None:
    async with _client() as client:
        creada = await _crear(client, admin, name="Escuadrilla 1")
        asociada = await client.patch(
            f"{URL}/{creada['id']}", json={"app_user_id": str(celular.id)}, headers=_auth(admin)
        )
        renombrada = await client.patch(
            f"{URL}/{creada['id']}", json={"name": "Escuadrilla Uno"}, headers=_auth(admin)
        )
        desasociada = await client.patch(
            f"{URL}/{creada['id']}", json={"app_user_id": None}, headers=_auth(admin)
        )

    assert asociada.json()["app_user"]["id"] == str(celular.id)
    # Cambiar solo el nombre no toca el usuario.
    assert renombrada.json()["app_user"]["id"] == str(celular.id)
    assert desasociada.status_code == 200
    assert desasociada.json()["app_user"] is None


@pytest.mark.parametrize(
    ("rol", "activo"),
    [(UserRole.technician, False), (UserRole.admin, True), (UserRole.owner, True)],
)
async def test_usuario_no_disponible_se_rechaza(admin: User, rol: UserRole, activo: bool) -> None:
    otro = make_user(email=f"otro-{rol.value}@ot-demo.com", role=rol, is_active=activo)
    await _seed([otro])

    async with _client() as client:
        response = await client.post(
            URL, json={"name": "Escuadrilla 1", "app_user_id": str(otro.id)}, headers=_auth(admin)
        )

    assert response.status_code == 422
    assert _code(response) == "crew_user_not_available"


async def test_usuario_inexistente_se_rechaza(admin: User) -> None:
    async with _client() as client:
        response = await client.post(
            URL,
            json={"name": "Escuadrilla 1", "app_user_id": str(uuid.uuid4())},
            headers=_auth(admin),
        )

    assert response.status_code == 422
    assert _code(response) == "crew_user_not_available"


async def test_usuario_de_otra_escuadrilla_se_rechaza(admin: User, celular: User) -> None:
    async with _client() as client:
        await _crear(client, admin, name="Escuadrilla 1", app_user_id=str(celular.id))
        segunda = await _crear(client, admin, name="Escuadrilla 2")
        response = await client.patch(
            f"{URL}/{segunda['id']}", json={"app_user_id": str(celular.id)}, headers=_auth(admin)
        )

    assert response.status_code == 422
    assert _code(response) == "crew_user_not_available"


async def test_reenviar_el_mismo_usuario_no_es_error(admin: User, celular: User) -> None:
    async with _client() as client:
        creada = await _crear(client, admin, name="Escuadrilla 1", app_user_id=str(celular.id))
        response = await client.patch(
            f"{URL}/{creada['id']}",
            json={"name": "Escuadrilla 1", "app_user_id": str(celular.id)},
            headers=_auth(admin),
        )

    assert response.status_code == 200, response.text


# Criterio 3: nombre repetido, sin distinguir mayúsculas ni espacios, también contra inactivas.
async def test_nombre_repetido_se_rechaza(admin: User) -> None:
    async with _client() as client:
        primera = await _crear(client, admin, name="Escuadrilla 1")
        await client.patch(
            f"{URL}/{primera['id']}", json={"is_active": False}, headers=_auth(admin)
        )
        repetida = await client.post(URL, json={"name": " ESCUADRILLA  1 "}, headers=_auth(admin))
        segunda = await _crear(client, admin, name="Escuadrilla 2")
        renombrada = await client.patch(
            f"{URL}/{segunda['id']}", json={"name": "escuadrilla 1"}, headers=_auth(admin)
        )

    assert repetida.status_code == 409
    assert _code(repetida) == "crew_name_already_exists"
    assert renombrada.status_code == 409


async def test_nombre_vacio_se_rechaza(admin: User) -> None:
    async with _client() as client:
        response = await client.post(URL, json={"name": "   "}, headers=_auth(admin))

    assert response.status_code == 422


# Criterio 4: desactivar la saca de las activas, sin borrarla.
async def test_desactivar_y_reactivar(admin: User) -> None:
    async with _client() as client:
        creada = await _crear(client, admin, name="Escuadrilla 1")
        desactivada = await client.patch(
            f"{URL}/{creada['id']}", json={"is_active": False}, headers=_auth(admin)
        )
        activas = await client.get(URL, headers=_auth(admin))
        todas = await client.get(f"{URL}?include_inactive=true", headers=_auth(admin))
        reactivada = await client.patch(
            f"{URL}/{creada['id']}", json={"is_active": True}, headers=_auth(admin)
        )

    assert desactivada.json()["is_active"] is False
    assert _nombres(activas) == []
    assert _nombres(todas) == ["Escuadrilla 1"]
    assert reactivada.json()["is_active"] is True


# Criterio 7: primero las activas, por nombre.
async def test_listado_activas_primero_por_nombre(admin: User) -> None:
    async with _client() as client:
        for nombre in ("Escuadrilla 3", "Escuadrilla 1", "Escuadrilla 2"):
            await _crear(client, admin, name=nombre)
        listado = await client.get(URL, headers=_auth(admin))
        una = listado.json()[0]
        await client.patch(f"{URL}/{una['id']}", json={"is_active": False}, headers=_auth(admin))
        todas = await client.get(f"{URL}?include_inactive=true", headers=_auth(admin))

    assert _nombres(listado) == ["Escuadrilla 1", "Escuadrilla 2", "Escuadrilla 3"]
    assert _nombres(todas) == ["Escuadrilla 2", "Escuadrilla 3", "Escuadrilla 1"]


async def test_consultar_y_no_encontrada(admin: User) -> None:
    async with _client() as client:
        creada = await _crear(client, admin, name="Escuadrilla 1")
        consultada = await client.get(f"{URL}/{creada['id']}", headers=_auth(admin))
        inexistente = await client.get(f"{URL}/{uuid.uuid4()}", headers=_auth(admin))
        editar_inexistente = await client.patch(
            f"{URL}/{uuid.uuid4()}", json={"name": "X"}, headers=_auth(admin)
        )

    assert consultada.json()["name"] == "Escuadrilla 1"
    assert inexistente.status_code == 404
    assert _code(inexistente) == "crew_not_found"
    assert editar_inexistente.status_code == 404


# Criterio 8: técnico (usuario de escuadrilla) y dirección reciben 403.
@pytest.mark.parametrize("rol", [UserRole.technician, UserRole.owner])
async def test_tecnico_y_direccion_no_gestionan_escuadrillas(schema: None, rol: UserRole) -> None:
    usuario = make_user(email=f"{rol.value}@ot-demo.com", role=rol)
    await _seed([usuario])

    async with _client() as client:
        listar = await client.get(URL, headers=_auth(usuario))
        crear = await client.post(URL, json={"name": "Escuadrilla 1"}, headers=_auth(usuario))

    assert listar.status_code == 403
    assert crear.status_code == 403
