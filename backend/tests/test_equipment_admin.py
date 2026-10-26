import uuid
from collections.abc import AsyncGenerator, Sequence
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import text

from app.core.security import create_access_token
from app.db.models.catalog import EquipmentType
from app.db.models.client import Client, ClientSite
from app.db.models.equipment import Equipment
from app.db.models.user import User, UserRole
from app.db.session import SessionLocal, engine
from app.main import app
from tests.factories import make_user

TABLES = [
    User.__table__,
    Client.__table__,
    ClientSite.__table__,
    EquipmentType.__table__,
    Equipment.__table__,
]
CLIENTS_URL = "/admin/clients"
EQUIPMENT_URL = "/admin/equipment"


@pytest.fixture
async def schema() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.create_all, tables=TABLES)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.drop_all, tables=list(reversed(TABLES)))
        await conn.execute(text("DROP TYPE IF EXISTS user_role"))
        await conn.execute(text("DROP TYPE IF EXISTS client_segment"))
        await conn.execute(text("DROP TYPE IF EXISTS tax_condition"))


@pytest.fixture
async def admin(schema: None) -> User:
    user = make_user(email="admin@ot-demo.com", role=UserRole.admin)
    await _seed([user])
    return user


@pytest.fixture
async def cliente(schema: None) -> Client:
    item = Client(number="10642", name="Hotel Ficticio")
    await _seed([item])
    return item


@pytest.fixture
async def sede(cliente: Client) -> ClientSite:
    item = ClientSite(client_id=cliente.id, label="Sede", address="Calle 1")
    await _seed([item])
    return item


@pytest.fixture
async def aire(schema: None) -> EquipmentType:
    item = EquipmentType(name="Aire acondicionado", code_prefix="EA")
    await _seed([item])
    return item


async def _seed(items: Sequence[object]) -> None:
    async with SessionLocal() as session:
        session.add_all(list(items))
        await session.commit()


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _equipment_url(client_id: object) -> str:
    return f"{CLIENTS_URL}/{client_id}/equipment"


async def _crear(
    client: AsyncClient, admin: User, client_id: object, **payload: object
) -> dict[str, object]:
    response = await client.post(_equipment_url(client_id), json=payload, headers=_auth(admin))
    assert response.status_code == 201, response.text
    body: dict[str, object] = response.json()
    return body


def _minimo(sede: ClientSite, tipo: EquipmentType, ubicacion: str = "Habitación 12") -> dict:
    return {
        "client_site_id": str(sede.id),
        "equipment_type_id": str(tipo.id),
        "location_note": ubicacion,
    }


def _code(response: Response) -> str:
    code: str = response.json()["detail"]["code"]
    return code


def _equipos_previos(sede: ClientSite, tipo: EquipmentType, cantidad: int) -> list[Equipment]:
    return [
        Equipment(
            client_site_id=sede.id,
            equipment_type_id=tipo.id,
            internal_code=f"PREVIO{n}",
            location_note=f"Previo {n}",
        )
        for n in range(1, cantidad + 1)
    ]


# Criterio 1: alcanza con domicilio, tipo y ubicación; el resto es opcional.
async def test_crear_equipo_con_lo_minimo(
    admin: User, cliente: Client, sede: ClientSite, aire: EquipmentType
) -> None:
    async with _client() as client:
        creado = await _crear(
            client, admin, cliente.id, **(_minimo(sede, aire, "  Habitación   12 "))
        )

    assert creado["client_site_id"] == str(sede.id)
    assert creado["equipment_type_id"] == str(aire.id)
    assert creado["location_note"] == "Habitación 12"
    assert creado["brand"] is None
    assert creado["model"] is None
    assert creado["serial_number"] is None
    assert creado["notes"] is None


async def test_crear_equipo_con_todos_los_datos(
    admin: User, cliente: Client, sede: ClientSite, aire: EquipmentType
) -> None:
    async with _client() as client:
        creado = await _crear(
            client,
            admin,
            cliente.id,
            **_minimo(sede, aire),
            brand="Marca Ficticia",
            model="Split 3000",
            serial_number="SN-0001",
            notes="3000 fg, gas R410A.",
        )

    assert creado["brand"] == "Marca Ficticia"
    assert creado["model"] == "Split 3000"
    assert creado["serial_number"] == "SN-0001"
    assert creado["notes"] == "3000 fg, gas R410A."


# Criterio 2: código = prefijo del tipo + dígitos del número de cliente + correlativo.
async def test_codigo_generado_con_prefijo_numero_y_correlativo(
    admin: User, cliente: Client, sede: ClientSite, aire: EquipmentType
) -> None:
    heladera = EquipmentType(name="Heladera comercial", code_prefix="EH")
    await _seed([heladera])
    async with _client() as client:
        primero = await _crear(client, admin, cliente.id, **_minimo(sede, aire))
        segundo = await _crear(client, admin, cliente.id, **_minimo(sede, heladera))

    assert primero["internal_code"] == "EA1064201"
    # El correlativo es por cliente, sin importar el tipo.
    assert segundo["internal_code"] == "EH1064202"


async def test_codigo_usa_eo_si_el_tipo_no_tiene_prefijo(
    admin: User, cliente: Client, sede: ClientSite
) -> None:
    nuevo = EquipmentType(name="Tipo nuevo")
    await _seed([nuevo])
    async with _client() as client:
        creado = await _crear(client, admin, cliente.id, **_minimo(sede, nuevo))

    assert creado["internal_code"] == "EO1064201"


async def test_codigo_toma_solo_los_digitos_del_numero_de_cliente(
    admin: User, aire: EquipmentType
) -> None:
    migrado = Client(number="CLI-00123", name="Cliente Migrado")
    await _seed([migrado])
    sede = ClientSite(client_id=migrado.id, address="Calle 2")
    await _seed([sede])
    async with _client() as client:
        creado = await _crear(client, admin, migrado.id, **_minimo(sede, aire))

    assert creado["internal_code"] == "EA0012301"


async def test_codigo_no_se_puede_mandar_al_crear_ni_editar(
    admin: User, cliente: Client, sede: ClientSite, aire: EquipmentType
) -> None:
    async with _client() as client:
        al_crear = await client.post(
            _equipment_url(cliente.id),
            json={**_minimo(sede, aire), "internal_code": "EA999"},
            headers=_auth(admin),
        )
        creado = await _crear(client, admin, cliente.id, **_minimo(sede, aire))
        al_editar = await client.patch(
            f"{EQUIPMENT_URL}/{creado['id']}",
            json={"internal_code": "EA999"},
            headers=_auth(admin),
        )

    assert al_crear.status_code == 422
    assert al_editar.status_code == 422


# Criterio 3: después del 99 sigue el 100; cuentan también los dados de baja.
async def test_correlativo_pasa_a_100_y_cuenta_los_dados_de_baja(
    admin: User, cliente: Client, sede: ClientSite, aire: EquipmentType
) -> None:
    previos = _equipos_previos(sede, aire, 99)
    previos[0].deleted_at = datetime.now(UTC)
    await _seed(previos)
    async with _client() as client:
        creado = await _crear(client, admin, cliente.id, **_minimo(sede, aire))

    assert creado["internal_code"] == "EA10642100"


# Criterio 4: si el código generado ya existe en otro cliente, se prueba el siguiente.
async def test_codigo_existente_en_otro_cliente_usa_el_siguiente(
    admin: User, cliente: Client, sede: ClientSite, aire: EquipmentType
) -> None:
    otro = Client(number="5", name="Otro Cliente")
    await _seed([otro])
    sede_otro = ClientSite(client_id=otro.id, address="Calle 3")
    await _seed([sede_otro])
    # Código migrado de Persat que coincide con el que tocaría generar.
    await _seed(
        [
            Equipment(
                client_site_id=sede_otro.id,
                equipment_type_id=aire.id,
                internal_code="EA1064201",
                location_note="Migrado",
            )
        ]
    )
    async with _client() as client:
        creado = await _crear(client, admin, cliente.id, **_minimo(sede, aire))

    assert creado["internal_code"] == "EA1064202"


# Criterio 5: cambiar ubicación, domicilio, tipo o datos conserva el código.
async def test_editar_y_mudar_conserva_el_codigo(
    admin: User, cliente: Client, sede: ClientSite, aire: EquipmentType
) -> None:
    otra_sede = ClientSite(client_id=cliente.id, address="Calle 9")
    freezer = EquipmentType(name="Freezer", code_prefix="EF")
    await _seed([otra_sede, freezer])
    async with _client() as client:
        creado = await _crear(client, admin, cliente.id, **_minimo(sede, aire), brand="Marca")
        url = f"{EQUIPMENT_URL}/{creado['id']}"
        editado = await client.patch(
            url,
            json={
                "client_site_id": str(otra_sede.id),
                "equipment_type_id": str(freezer.id),
                "location_note": "Depósito",
                "model": "Modelo X",
            },
            headers=_auth(admin),
        )
        consultado = await client.get(url, headers=_auth(admin))

    assert editado.status_code == 200, editado.text
    body = consultado.json()
    assert body["internal_code"] == creado["internal_code"]
    assert body["client_site_id"] == str(otra_sede.id)
    assert body["equipment_type_id"] == str(freezer.id)
    assert body["location_note"] == "Depósito"
    assert body["brand"] == "Marca"
    assert body["model"] == "Modelo X"


async def test_editar_borra_opcionales_en_null(
    admin: User, cliente: Client, sede: ClientSite, aire: EquipmentType
) -> None:
    async with _client() as client:
        creado = await _crear(client, admin, cliente.id, **_minimo(sede, aire), brand="Marca")
        editado = await client.patch(
            f"{EQUIPMENT_URL}/{creado['id']}",
            json={"brand": None, "notes": "   "},
            headers=_auth(admin),
        )

    assert editado.json()["brand"] is None
    assert editado.json()["notes"] is None


# Criterio 6: listado del cliente ordenado por ubicación, con filtro por domicilio.
async def test_listado_del_cliente_con_filtro_por_domicilio(
    admin: User, cliente: Client, sede: ClientSite, aire: EquipmentType
) -> None:
    otra_sede = ClientSite(client_id=cliente.id, address="Calle 9")
    otro = Client(number="5", name="Otro Cliente")
    await _seed([otra_sede, otro])
    sede_otro = ClientSite(client_id=otro.id, address="Calle 3")
    await _seed([sede_otro])
    async with _client() as client:
        await _crear(client, admin, cliente.id, **_minimo(sede, aire, "Oficina"))
        await _crear(client, admin, cliente.id, **_minimo(otra_sede, aire, "Cocina"))
        await _crear(client, admin, otro.id, **_minimo(sede_otro, aire, "De otro"))
        todos = await client.get(_equipment_url(cliente.id), headers=_auth(admin))
        filtrados = await client.get(
            _equipment_url(cliente.id), params={"site_id": str(sede.id)}, headers=_auth(admin)
        )

    assert [e["location_note"] for e in todos.json()] == ["Cocina", "Oficina"]
    assert [e["location_note"] for e in filtrados.json()] == ["Oficina"]


async def test_listado_excluye_dados_de_baja(
    admin: User, cliente: Client, sede: ClientSite, aire: EquipmentType
) -> None:
    previos = _equipos_previos(sede, aire, 2)
    previos[0].deleted_at = datetime.now(UTC)
    await _seed(previos)
    async with _client() as client:
        listado = await client.get(_equipment_url(cliente.id), headers=_auth(admin))

    assert [e["location_note"] for e in listado.json()] == ["Previo 2"]


# Criterio 7: cada domicilio muestra su cantidad de equipos (sin los dados de baja).
async def test_domicilios_muestran_cantidad_de_equipos(
    admin: User, cliente: Client, sede: ClientSite, aire: EquipmentType
) -> None:
    vacia = ClientSite(client_id=cliente.id, address="Calle 9")
    previos = _equipos_previos(sede, aire, 3)
    previos[0].deleted_at = datetime.now(UTC)
    await _seed([vacia, *previos])
    async with _client() as client:
        listado = await client.get(f"{CLIENTS_URL}/{cliente.id}/sites", headers=_auth(admin))
        una = await client.get(f"/admin/sites/{sede.id}", headers=_auth(admin))

    assert {s["address"]: s["equipment_count"] for s in listado.json()} == {
        "Calle 1": 2,
        "Calle 9": 0,
    }
    assert una.json()["equipment_count"] == 2


# Criterio 8: un domicilio o tipo inactivo no se puede elegir.
async def test_domicilio_o_tipo_inactivo_se_rechaza(
    admin: User, cliente: Client, sede: ClientSite, aire: EquipmentType
) -> None:
    sede_inactiva = ClientSite(client_id=cliente.id, address="Calle 9", is_active=False)
    tipo_inactivo = EquipmentType(name="Viejo", code_prefix="EV", is_active=False)
    await _seed([sede_inactiva, tipo_inactivo])
    async with _client() as client:
        en_sede_inactiva = await client.post(
            _equipment_url(cliente.id), json=_minimo(sede_inactiva, aire), headers=_auth(admin)
        )
        con_tipo_inactivo = await client.post(
            _equipment_url(cliente.id), json=_minimo(sede, tipo_inactivo), headers=_auth(admin)
        )
        creado = await _crear(client, admin, cliente.id, **_minimo(sede, aire))
        mudanza = await client.patch(
            f"{EQUIPMENT_URL}/{creado['id']}",
            json={"client_site_id": str(sede_inactiva.id)},
            headers=_auth(admin),
        )

    assert en_sede_inactiva.status_code == 422
    assert _code(en_sede_inactiva) == "site_inactive"
    assert con_tipo_inactivo.status_code == 422
    assert _code(con_tipo_inactivo) == "equipment_type_inactive"
    assert mudanza.status_code == 422
    assert _code(mudanza) == "site_inactive"


async def test_equipo_en_domicilio_inactivo_se_puede_editar(
    admin: User, cliente: Client, sede: ClientSite, aire: EquipmentType
) -> None:
    async with _client() as client:
        creado = await _crear(client, admin, cliente.id, **_minimo(sede, aire))
        await client.patch(
            f"/admin/sites/{sede.id}", json={"is_active": False}, headers=_auth(admin)
        )
        editado = await client.patch(
            f"{EQUIPMENT_URL}/{creado['id']}",
            json={"location_note": "Otra"},
            headers=_auth(admin),
        )

    assert editado.status_code == 200, editado.text


# Criterio 9: ubicación vacía o domicilio de otro cliente se rechaza con 422.
async def test_ubicacion_vacia_o_domicilio_de_otro_cliente_se_rechaza(
    admin: User, cliente: Client, sede: ClientSite, aire: EquipmentType
) -> None:
    otro = Client(number="5", name="Otro Cliente")
    await _seed([otro])
    sede_otro = ClientSite(client_id=otro.id, address="Calle 3")
    await _seed([sede_otro])
    async with _client() as client:
        vacia = await client.post(
            _equipment_url(cliente.id), json=_minimo(sede, aire, "   "), headers=_auth(admin)
        )
        ajena = await client.post(
            _equipment_url(cliente.id), json=_minimo(sede_otro, aire), headers=_auth(admin)
        )
        creado = await _crear(client, admin, cliente.id, **_minimo(sede, aire))
        mudanza_ajena = await client.patch(
            f"{EQUIPMENT_URL}/{creado['id']}",
            json={"client_site_id": str(sede_otro.id)},
            headers=_auth(admin),
        )
        ubicacion_nula = await client.patch(
            f"{EQUIPMENT_URL}/{creado['id']}", json={"location_note": None}, headers=_auth(admin)
        )

    assert vacia.status_code == 422
    assert ajena.status_code == 422
    assert _code(ajena) == "site_of_another_client"
    assert mudanza_ajena.status_code == 422
    assert _code(mudanza_ajena) == "site_of_another_client"
    assert ubicacion_nula.status_code == 422


# Criterio 10: cliente, domicilio, tipo o equipo inexistente da 404.
async def test_inexistentes_dan_404(
    admin: User, cliente: Client, sede: ClientSite, aire: EquipmentType
) -> None:
    async with _client() as client:
        sin_cliente = await client.post(
            _equipment_url(uuid.uuid4()), json=_minimo(sede, aire), headers=_auth(admin)
        )
        listado = await client.get(_equipment_url(uuid.uuid4()), headers=_auth(admin))
        sin_sede = await client.post(
            _equipment_url(cliente.id),
            json={**_minimo(sede, aire), "client_site_id": str(uuid.uuid4())},
            headers=_auth(admin),
        )
        sin_tipo = await client.post(
            _equipment_url(cliente.id),
            json={**_minimo(sede, aire), "equipment_type_id": str(uuid.uuid4())},
            headers=_auth(admin),
        )
        sin_equipo = await client.get(f"{EQUIPMENT_URL}/{uuid.uuid4()}", headers=_auth(admin))
        editar = await client.patch(
            f"{EQUIPMENT_URL}/{uuid.uuid4()}", json={"location_note": "X"}, headers=_auth(admin)
        )

    assert [_code(r) for r in (sin_cliente, listado, sin_sede, sin_tipo, sin_equipo, editar)] == [
        "client_not_found",
        "client_not_found",
        "site_not_found",
        "equipment_type_not_found",
        "equipment_not_found",
        "equipment_not_found",
    ]


# No hay borrado en esta historia: la baja lógica llega con E03-07.
async def test_no_hay_ruta_para_borrar_un_equipo(
    admin: User, cliente: Client, sede: ClientSite, aire: EquipmentType
) -> None:
    async with _client() as client:
        creado = await _crear(client, admin, cliente.id, **_minimo(sede, aire))
        response = await client.delete(f"{EQUIPMENT_URL}/{creado['id']}", headers=_auth(admin))

    assert response.status_code == 405


# Criterio 11: técnico y dirección reciben acceso denegado.
@pytest.mark.parametrize("role", [UserRole.technician, UserRole.owner])
async def test_tecnico_y_direccion_reciben_403(
    cliente: Client, sede: ClientSite, aire: EquipmentType, role: UserRole
) -> None:
    usuario = make_user(email=f"{role.value}@ot-demo.com", role=role)
    equipo = _equipos_previos(sede, aire, 1)[0]
    await _seed([usuario, equipo])
    async with _client() as client:
        respuestas = [
            await client.get(_equipment_url(cliente.id), headers=_auth(usuario)),
            await client.post(
                _equipment_url(cliente.id), json=_minimo(sede, aire), headers=_auth(usuario)
            ),
            await client.get(f"{EQUIPMENT_URL}/{equipo.id}", headers=_auth(usuario)),
            await client.patch(
                f"{EQUIPMENT_URL}/{equipo.id}", json={"brand": "X"}, headers=_auth(usuario)
            ),
        ]

    assert [r.status_code for r in respuestas] == [403] * len(respuestas)
