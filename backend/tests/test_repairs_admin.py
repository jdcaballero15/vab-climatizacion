from collections.abc import AsyncGenerator, Sequence

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.security import create_access_token
from app.db.models.catalog import EquipmentType, Repair
from app.db.models.user import User, UserRole
from app.db.session import SessionLocal, engine
from app.main import app
from tests.factories import make_user

TABLES = [User.__table__, EquipmentType.__table__, Repair.__table__]
URL = "/admin/repairs"
NO_EXISTE = "00000000-0000-0000-0000-000000000000"


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
async def split(schema: None) -> EquipmentType:
    return await _equipment_type("Split")


@pytest.fixture
async def freezer(schema: None) -> EquipmentType:
    return await _equipment_type("Freezer")


async def _equipment_type(name: str) -> EquipmentType:
    equipment_type = EquipmentType(name=name, is_active=True)
    await _seed([equipment_type])
    return equipment_type


async def _seed(items: Sequence[User | EquipmentType]) -> None:
    async with SessionLocal() as session:
        session.add_all(list(items))
        await session.commit()


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _crear(
    client: AsyncClient, admin: User, name: str, equipment_type: EquipmentType | None = None
) -> Response:
    body = {"name": name, "equipment_type_id": str(equipment_type.id) if equipment_type else None}
    return await client.post(URL, json=body, headers=_auth(admin))


async def _crear_ok(
    client: AsyncClient, admin: User, name: str, equipment_type: EquipmentType | None = None
) -> dict[str, object]:
    response = await _crear(client, admin, name, equipment_type)
    assert response.status_code == 201, response.text
    body: dict[str, object] = response.json()
    return body


async def _listar(
    client: AsyncClient,
    admin: User,
    equipment_type: EquipmentType | None = None,
    *,
    include_inactive: bool = False,
) -> list[str]:
    params: dict[str, str] = {"include_inactive": str(include_inactive).lower()}
    if equipment_type is not None:
        params["equipment_type_id"] = str(equipment_type.id)
    response = await client.get(URL, params=params, headers=_auth(admin))
    assert response.status_code == 200, response.text
    return [item["name"] for item in response.json()]


# Criterio 1: una reparacion de un tipo queda activa y aparece en las activas de ese tipo.
async def test_crear_reparacion_de_un_tipo(
    admin: User, split: EquipmentType, freezer: EquipmentType
) -> None:
    async with _client() as client:
        creada = await _crear_ok(client, admin, "Carga de gas", split)
        de_split = await _listar(client, admin, split)
        de_freezer = await _listar(client, admin, freezer)

    assert creada["is_active"] is True
    assert creada["equipment_type_id"] == str(split.id)
    assert de_split == ["Carga de gas"]
    assert de_freezer == []


# Criterio 2: una reparacion sin tipo es genérica y aparece en todos los tipos.
async def test_reparacion_generica_aparece_en_todos_los_tipos(
    admin: User, split: EquipmentType, freezer: EquipmentType
) -> None:
    async with _client() as client:
        creada = await _crear_ok(client, admin, "Cambio de capacitor")
        await _crear_ok(client, admin, "Limpieza de drenaje", split)
        de_split = await _listar(client, admin, split)
        de_freezer = await _listar(client, admin, freezer)
        todas = await _listar(client, admin)

    assert creada["equipment_type_id"] is None
    assert de_split == ["Cambio de capacitor", "Limpieza de drenaje"]
    assert de_freezer == ["Cambio de capacitor"]
    assert todas == ["Cambio de capacitor", "Limpieza de drenaje"]


async def test_listar_reparaciones_de_un_tipo_inexistente_devuelve_404(admin: User) -> None:
    async with _client() as client:
        response = await client.get(
            URL, params={"equipment_type_id": NO_EXISTE}, headers=_auth(admin)
        )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "equipment_type_not_found"


# Criterio 3: renombrar se ve en todo lugar que la referencia por id.
async def test_renombrar_reparacion_se_ve_por_id(admin: User, split: EquipmentType) -> None:
    async with _client() as client:
        reparacion = await _crear_ok(client, admin, "Reparacion de placa", split)
        renombrada = await client.patch(
            f"{URL}/{reparacion['id']}", json={"name": "Carga de gas"}, headers=_auth(admin)
        )
        consultada = await client.get(f"{URL}/{reparacion['id']}", headers=_auth(admin))

    assert renombrada.status_code == 200
    assert consultada.json() == {
        "id": reparacion["id"],
        "equipment_type_id": str(split.id),
        "name": "Carga de gas",
        "is_active": True,
    }


async def test_reparacion_inexistente_devuelve_404(admin: User) -> None:
    async with _client() as client:
        consultada = await client.get(f"{URL}/{NO_EXISTE}", headers=_auth(admin))
        editada = await client.patch(
            f"{URL}/{NO_EXISTE}", json={"is_active": False}, headers=_auth(admin)
        )
    for response in (consultada, editada):
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "repair_not_found"


# Criterio 4: desactivar saca de las activas, se consulta por id y se reactiva.
async def test_desactivar_y_reactivar_reparacion(admin: User, split: EquipmentType) -> None:
    async with _client() as client:
        reparacion = await _crear_ok(client, admin, "Ajuste de ventilador", split)
        url = f"{URL}/{reparacion['id']}"

        await client.patch(url, json={"is_active": False}, headers=_auth(admin))
        activas = await _listar(client, admin, split)
        todas = await _listar(client, admin, split, include_inactive=True)
        consultada = await client.get(url, headers=_auth(admin))

        await client.patch(url, json={"is_active": True}, headers=_auth(admin))
        reactivadas = await _listar(client, admin, split)

    assert activas == []
    assert todas == ["Ajuste de ventilador"]
    assert consultada.json()["is_active"] is False
    assert reactivadas == ["Ajuste de ventilador"]


# Criterio 5: un tipo desactivado no ofrece sus reparaciones específicas; las genéricas siguen.
async def test_tipo_desactivado_solo_ofrece_genericas(admin: User, split: EquipmentType) -> None:
    async with _client() as client:
        await _crear_ok(client, admin, "Cambio de capacitor")
        await _crear_ok(client, admin, "Limpieza de drenaje", split)
        await client.patch(
            f"/admin/equipment-types/{split.id}", json={"is_active": False}, headers=_auth(admin)
        )
        activas = await _listar(client, admin, split)
        todas = await _listar(client, admin, split, include_inactive=True)

    assert activas == ["Cambio de capacitor"]
    assert todas == ["Cambio de capacitor", "Limpieza de drenaje"]


# Criterio 6: duplicados sin distinguir mayúsculas ni espacios, en el mismo tipo,
# entre genéricas y entre una genérica y una específica de cualquier tipo.
@pytest.mark.parametrize(
    "duplicado", ["Carga de gas", "carga de gas", "  CARGA DE GAS  ", "Carga   de gas"]
)
async def test_duplicado_en_el_mismo_tipo_se_rechaza(
    admin: User, split: EquipmentType, duplicado: str
) -> None:
    async with _client() as client:
        await _crear_ok(client, admin, "Carga de gas", split)
        response = await _crear(client, admin, duplicado, split)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "repair_name_already_exists"


async def test_duplicado_entre_genericas_se_rechaza(admin: User) -> None:
    async with _client() as client:
        await _crear_ok(client, admin, "Cambio de capacitor")
        response = await _crear(client, admin, "cambio de capacitor")
    assert response.status_code == 409


async def test_la_base_rechaza_genericas_duplicadas_aunque_no_pase_por_el_servicio(
    schema: None,
) -> None:
    # Respaldo ante dos guardados simultáneos: sin el coalesce del índice, dos NULL no chocan.
    async with SessionLocal() as session:
        session.add_all(
            [
                Repair(name="Ajuste de ventilador", is_active=True),
                Repair(name="ajuste de ventilador", is_active=True),
            ]
        )
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_especifica_con_el_nombre_de_una_generica_se_rechaza(
    admin: User, split: EquipmentType
) -> None:
    async with _client() as client:
        await _crear_ok(client, admin, "Cambio de capacitor")
        response = await _crear(client, admin, "Cambio de capacitor", split)
    assert response.status_code == 409


async def test_generica_con_el_nombre_de_una_especifica_se_rechaza(
    admin: User, freezer: EquipmentType
) -> None:
    async with _client() as client:
        await _crear_ok(client, admin, "Descongelado", freezer)
        response = await _crear(client, admin, "Descongelado")
    assert response.status_code == 409


async def test_duplicado_contra_reparacion_inactiva_se_rechaza(
    admin: User, split: EquipmentType
) -> None:
    async with _client() as client:
        reparacion = await _crear_ok(client, admin, "Ajuste de ventilador", split)
        await client.patch(
            f"{URL}/{reparacion['id']}", json={"is_active": False}, headers=_auth(admin)
        )
        response = await _crear(client, admin, "ajuste de ventilador", split)
    assert response.status_code == 409


async def test_mismo_nombre_en_dos_tipos_se_acepta(
    admin: User, split: EquipmentType, freezer: EquipmentType
) -> None:
    async with _client() as client:
        await _crear_ok(client, admin, "Carga de gas", split)
        response = await _crear(client, admin, "Carga de gas", freezer)
    assert response.status_code == 201


async def test_renombrar_a_un_nombre_existente_se_rechaza(
    admin: User, split: EquipmentType
) -> None:
    async with _client() as client:
        await _crear_ok(client, admin, "Cambio de capacitor")
        reparacion = await _crear_ok(client, admin, "Ajuste de ventilador", split)
        response = await client.patch(
            f"{URL}/{reparacion['id']}", json={"name": "CAMBIO DE CAPACITOR"}, headers=_auth(admin)
        )
    assert response.status_code == 409


async def test_renombrar_cambiando_solo_mayusculas_se_acepta(
    admin: User, split: EquipmentType
) -> None:
    async with _client() as client:
        reparacion = await _crear_ok(client, admin, "ajuste de ventilador", split)
        response = await client.patch(
            f"{URL}/{reparacion['id']}", json={"name": "Ajuste de ventilador"}, headers=_auth(admin)
        )
    assert response.status_code == 200
    assert response.json()["name"] == "Ajuste de ventilador"


async def test_los_acentos_distinguen_nombres(admin: User, split: EquipmentType) -> None:
    async with _client() as client:
        await _crear_ok(client, admin, "Reparación de placa", split)
        response = await _crear(client, admin, "Reparacion de placa", split)
    assert response.status_code == 201


async def test_el_nombre_se_guarda_sin_espacios_sobrantes(admin: User) -> None:
    async with _client() as client:
        creada = await _crear_ok(client, admin, "  Cambio   de   filtro  ")
    assert creada["name"] == "Cambio de filtro"


# Criterio 7: un nombre vacío o de solo espacios se rechaza con 422.
@pytest.mark.parametrize("vacio", ["", "   "])
async def test_nombre_vacio_se_rechaza(admin: User, vacio: str) -> None:
    async with _client() as client:
        reparacion = await _crear_ok(client, admin, "Ajuste de ventilador")
        crear = await _crear(client, admin, vacio)
        renombrar = await client.patch(
            f"{URL}/{reparacion['id']}", json={"name": vacio}, headers=_auth(admin)
        )
    assert crear.status_code == 422
    assert renombrar.status_code == 422


# Criterio 8: crear una reparacion para un tipo de equipo inexistente da 404.
async def test_crear_reparacion_para_tipo_inexistente_devuelve_404(admin: User) -> None:
    async with _client() as client:
        response = await client.post(
            URL,
            json={"name": "Ajuste de ventilador", "equipment_type_id": NO_EXISTE},
            headers=_auth(admin),
        )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "equipment_type_not_found"


# Criterio 10: técnico y dirección reciben 403 en todo el catálogo, también al leer.
@pytest.mark.parametrize("role", [UserRole.technician, UserRole.owner])
async def test_tecnico_y_direccion_reciben_403(
    admin: User, split: EquipmentType, role: UserRole
) -> None:
    otro = make_user(email="otro@ot-demo.com", role=role)
    await _seed([otro])
    async with _client() as client:
        reparacion = await _crear_ok(client, admin, "Ajuste de ventilador", split)
        reparacion_url = f"{URL}/{reparacion['id']}"
        respuestas = [
            await client.get(URL, headers=_auth(otro)),
            await client.get(URL, params={"equipment_type_id": str(split.id)}, headers=_auth(otro)),
            await client.post(URL, json={"name": "X"}, headers=_auth(otro)),
            await client.get(reparacion_url, headers=_auth(otro)),
            await client.patch(reparacion_url, json={"name": "X"}, headers=_auth(otro)),
            await client.patch(reparacion_url, json={"is_active": False}, headers=_auth(otro)),
        ]
    assert [r.status_code for r in respuestas] == [403] * len(respuestas)
