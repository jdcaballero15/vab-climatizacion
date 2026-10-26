from collections.abc import AsyncGenerator, Sequence

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.security import create_access_token
from app.db.models.catalog import EquipmentType, Failure
from app.db.models.user import User, UserRole
from app.db.session import SessionLocal, engine
from app.main import app
from tests.factories import make_user

TABLES = [User.__table__, EquipmentType.__table__, Failure.__table__]
URL = "/admin/failures"
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


# Criterio 1: una falla de un tipo queda activa y aparece en las activas de ese tipo.
async def test_crear_falla_de_un_tipo(
    admin: User, split: EquipmentType, freezer: EquipmentType
) -> None:
    async with _client() as client:
        creada = await _crear_ok(client, admin, "No enfría", split)
        de_split = await _listar(client, admin, split)
        de_freezer = await _listar(client, admin, freezer)

    assert creada["is_active"] is True
    assert creada["equipment_type_id"] == str(split.id)
    assert de_split == ["No enfría"]
    assert de_freezer == []


# Criterio 2: una falla sin tipo es genérica y aparece en todos los tipos.
async def test_falla_generica_aparece_en_todos_los_tipos(
    admin: User, split: EquipmentType, freezer: EquipmentType
) -> None:
    async with _client() as client:
        creada = await _crear_ok(client, admin, "No enciende")
        await _crear_ok(client, admin, "Pierde agua", split)
        de_split = await _listar(client, admin, split)
        de_freezer = await _listar(client, admin, freezer)
        todas = await _listar(client, admin)

    assert creada["equipment_type_id"] is None
    assert de_split == ["No enciende", "Pierde agua"]
    assert de_freezer == ["No enciende"]
    assert todas == ["No enciende", "Pierde agua"]


async def test_listar_fallas_de_un_tipo_inexistente_devuelve_404(admin: User) -> None:
    async with _client() as client:
        response = await client.get(
            URL, params={"equipment_type_id": NO_EXISTE}, headers=_auth(admin)
        )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "equipment_type_not_found"


# Criterio 3: renombrar se ve en todo lugar que la referencia por id.
async def test_renombrar_falla_se_ve_por_id(admin: User, split: EquipmentType) -> None:
    async with _client() as client:
        falla = await _crear_ok(client, admin, "No enfria", split)
        renombrada = await client.patch(
            f"{URL}/{falla['id']}", json={"name": "No enfría"}, headers=_auth(admin)
        )
        consultada = await client.get(f"{URL}/{falla['id']}", headers=_auth(admin))

    assert renombrada.status_code == 200
    assert consultada.json() == {
        "id": falla["id"],
        "equipment_type_id": str(split.id),
        "name": "No enfría",
        "is_active": True,
    }


async def test_falla_inexistente_devuelve_404(admin: User) -> None:
    async with _client() as client:
        consultada = await client.get(f"{URL}/{NO_EXISTE}", headers=_auth(admin))
        editada = await client.patch(
            f"{URL}/{NO_EXISTE}", json={"is_active": False}, headers=_auth(admin)
        )
    for response in (consultada, editada):
        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "failure_not_found"


# Criterio 4: desactivar saca de las activas, se consulta por id y se reactiva.
async def test_desactivar_y_reactivar_falla(admin: User, split: EquipmentType) -> None:
    async with _client() as client:
        falla = await _crear_ok(client, admin, "Ruido", split)
        url = f"{URL}/{falla['id']}"

        await client.patch(url, json={"is_active": False}, headers=_auth(admin))
        activas = await _listar(client, admin, split)
        todas = await _listar(client, admin, split, include_inactive=True)
        consultada = await client.get(url, headers=_auth(admin))

        await client.patch(url, json={"is_active": True}, headers=_auth(admin))
        reactivadas = await _listar(client, admin, split)

    assert activas == []
    assert todas == ["Ruido"]
    assert consultada.json()["is_active"] is False
    assert reactivadas == ["Ruido"]


# Criterio 5: un tipo desactivado no ofrece sus fallas específicas; las genéricas siguen.
async def test_tipo_desactivado_solo_ofrece_genericas(admin: User, split: EquipmentType) -> None:
    async with _client() as client:
        await _crear_ok(client, admin, "No enciende")
        await _crear_ok(client, admin, "Pierde agua", split)
        await client.patch(
            f"/admin/equipment-types/{split.id}", json={"is_active": False}, headers=_auth(admin)
        )
        activas = await _listar(client, admin, split)
        todas = await _listar(client, admin, split, include_inactive=True)

    assert activas == ["No enciende"]
    assert todas == ["No enciende", "Pierde agua"]


# Criterio 6: duplicados sin distinguir mayúsculas ni espacios, en el mismo tipo,
# entre genéricas y entre una genérica y una específica de cualquier tipo.
@pytest.mark.parametrize("duplicado", ["No enfría", "no enfría", "  NO ENFRÍA  ", "No   enfría"])
async def test_duplicado_en_el_mismo_tipo_se_rechaza(
    admin: User, split: EquipmentType, duplicado: str
) -> None:
    async with _client() as client:
        await _crear_ok(client, admin, "No enfría", split)
        response = await _crear(client, admin, duplicado, split)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "failure_name_already_exists"


async def test_duplicado_entre_genericas_se_rechaza(admin: User) -> None:
    async with _client() as client:
        await _crear_ok(client, admin, "No enciende")
        response = await _crear(client, admin, "no enciende")
    assert response.status_code == 409


async def test_la_base_rechaza_genericas_duplicadas_aunque_no_pase_por_el_servicio(
    schema: None,
) -> None:
    # Respaldo ante dos guardados simultáneos: sin el coalesce del índice, dos NULL no chocan.
    async with SessionLocal() as session:
        session.add_all(
            [Failure(name="Ruido", is_active=True), Failure(name="ruido", is_active=True)]
        )
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_especifica_con_el_nombre_de_una_generica_se_rechaza(
    admin: User, split: EquipmentType
) -> None:
    async with _client() as client:
        await _crear_ok(client, admin, "No enciende")
        response = await _crear(client, admin, "No enciende", split)
    assert response.status_code == 409


async def test_generica_con_el_nombre_de_una_especifica_se_rechaza(
    admin: User, freezer: EquipmentType
) -> None:
    async with _client() as client:
        await _crear_ok(client, admin, "Escarcha", freezer)
        response = await _crear(client, admin, "Escarcha")
    assert response.status_code == 409


async def test_duplicado_contra_falla_inactiva_se_rechaza(
    admin: User, split: EquipmentType
) -> None:
    async with _client() as client:
        falla = await _crear_ok(client, admin, "Ruido", split)
        await client.patch(f"{URL}/{falla['id']}", json={"is_active": False}, headers=_auth(admin))
        response = await _crear(client, admin, "ruido", split)
    assert response.status_code == 409


async def test_mismo_nombre_en_dos_tipos_se_acepta(
    admin: User, split: EquipmentType, freezer: EquipmentType
) -> None:
    async with _client() as client:
        await _crear_ok(client, admin, "No enfría", split)
        response = await _crear(client, admin, "No enfría", freezer)
    assert response.status_code == 201


async def test_renombrar_a_un_nombre_existente_se_rechaza(
    admin: User, split: EquipmentType
) -> None:
    async with _client() as client:
        await _crear_ok(client, admin, "No enciende")
        falla = await _crear_ok(client, admin, "Ruido", split)
        response = await client.patch(
            f"{URL}/{falla['id']}", json={"name": "NO ENCIENDE"}, headers=_auth(admin)
        )
    assert response.status_code == 409


async def test_renombrar_cambiando_solo_mayusculas_se_acepta(
    admin: User, split: EquipmentType
) -> None:
    async with _client() as client:
        falla = await _crear_ok(client, admin, "ruido", split)
        response = await client.patch(
            f"{URL}/{falla['id']}", json={"name": "Ruido"}, headers=_auth(admin)
        )
    assert response.status_code == 200
    assert response.json()["name"] == "Ruido"


async def test_los_acentos_distinguen_nombres(admin: User, split: EquipmentType) -> None:
    async with _client() as client:
        await _crear_ok(client, admin, "No enfría", split)
        response = await _crear(client, admin, "No enfria", split)
    assert response.status_code == 201


async def test_el_nombre_se_guarda_sin_espacios_sobrantes(admin: User) -> None:
    async with _client() as client:
        creada = await _crear_ok(client, admin, "  Pierde   gas  ")
    assert creada["name"] == "Pierde gas"


# Criterio 7: un nombre vacío o de solo espacios se rechaza con 422.
@pytest.mark.parametrize("vacio", ["", "   "])
async def test_nombre_vacio_se_rechaza(admin: User, vacio: str) -> None:
    async with _client() as client:
        falla = await _crear_ok(client, admin, "Ruido")
        crear = await _crear(client, admin, vacio)
        renombrar = await client.patch(
            f"{URL}/{falla['id']}", json={"name": vacio}, headers=_auth(admin)
        )
    assert crear.status_code == 422
    assert renombrar.status_code == 422


# Criterio 8: crear una falla para un tipo de equipo inexistente da 404.
async def test_crear_falla_para_tipo_inexistente_devuelve_404(admin: User) -> None:
    async with _client() as client:
        response = await client.post(
            URL, json={"name": "Ruido", "equipment_type_id": NO_EXISTE}, headers=_auth(admin)
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
        falla = await _crear_ok(client, admin, "Ruido", split)
        falla_url = f"{URL}/{falla['id']}"
        respuestas = [
            await client.get(URL, headers=_auth(otro)),
            await client.get(URL, params={"equipment_type_id": str(split.id)}, headers=_auth(otro)),
            await client.post(URL, json={"name": "X"}, headers=_auth(otro)),
            await client.get(falla_url, headers=_auth(otro)),
            await client.patch(falla_url, json={"name": "X"}, headers=_auth(otro)),
            await client.patch(falla_url, json={"is_active": False}, headers=_auth(otro)),
        ]
    assert [r.status_code for r in respuestas] == [403] * len(respuestas)
