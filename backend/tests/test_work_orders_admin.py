import uuid
from collections.abc import AsyncGenerator, Sequence

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select, text

from app.core.security import create_access_token
from app.db.models.catalog import EquipmentType, WorkType
from app.db.models.client import Client, ClientSite
from app.db.models.equipment import Equipment
from app.db.models.user import User, UserRole
from app.db.models.work_order import WorkOrder, WorkOrderEvent
from app.db.session import SessionLocal, engine
from app.domain.work_order import OrderStatus, WorkOrderEventType
from app.main import app
from tests.factories import make_user, make_work_order

TABLES = [
    User.__table__,
    Client.__table__,
    ClientSite.__table__,
    EquipmentType.__table__,
    Equipment.__table__,
    WorkType.__table__,
    WorkOrder.__table__,
    WorkOrderEvent.__table__,
]
ORDERS_URL = "/admin/orders"
PENDING_URL = f"{ORDERS_URL}?status=pending"


@pytest.fixture
async def schema() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.create_all, tables=TABLES)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.drop_all, tables=list(reversed(TABLES)))
        for enum_type in (
            "user_role",
            "client_segment",
            "tax_condition",
            "order_status",
            "order_kind",
            "order_source",
            "order_channel",
        ):
            await conn.execute(text(f"DROP TYPE IF EXISTS {enum_type}"))
        await conn.execute(text("DROP SEQUENCE IF EXISTS work_order_number_seq"))


@pytest.fixture
async def admin(schema: None) -> User:
    user = make_user(email="admin@ot-demo.com", role=UserRole.admin)
    await _seed([user])
    return user


@pytest.fixture
async def cliente(schema: None) -> Client:
    item = Client(number="10642", name="Sanatorio Ficticio")
    await _seed([item])
    return item


@pytest.fixture
async def sede(cliente: Client) -> ClientSite:
    item = ClientSite(client_id=cliente.id, label="Central", address="Calle 1")
    await _seed([item])
    return item


@pytest.fixture
async def reparacion(schema: None) -> WorkType:
    item = WorkType(name="Reparación")
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


def _pedido(cliente: Client, sede: ClientSite, tipo: WorkType, **extra: object) -> dict:
    return {
        "client_id": str(cliente.id),
        "client_site_id": str(sede.id),
        "work_type_id": str(tipo.id),
        "channel": "whatsapp",
        "description": "No enfría la heladera del office",
        **extra,
    }


async def _crear(client: AsyncClient, admin: User, payload: dict) -> dict[str, object]:
    response = await client.post(ORDERS_URL, json=payload, headers=_auth(admin))
    assert response.status_code == 201, response.text
    body: dict[str, object] = response.json()
    return body


def _code(response: Response) -> str:
    code: str = response.json()["detail"]["code"]
    return code


def _faltantes(response: Response) -> set[str]:
    return {str(error["loc"][-1]) for error in response.json()["detail"]}


# Criterio 1: queda Pendiente con número correlativo.
async def test_crear_orden_queda_pendiente_con_numero_correlativo(
    admin: User, cliente: Client, sede: ClientSite, reparacion: WorkType
) -> None:
    async with _client() as client:
        primera = await _crear(client, admin, _pedido(cliente, sede, reparacion))
        segunda = await _crear(client, admin, _pedido(cliente, sede, reparacion))

    assert primera["status"] == "pending"
    assert primera["source"] == "manual"
    assert primera["kind"] == "on_site"
    assert primera["client_id"] == str(cliente.id)
    assert primera["client_site_id"] == str(sede.id)
    assert primera["work_type_id"] == str(reparacion.id)
    assert primera["description"] == "No enfría la heladera del office"
    assert isinstance(primera["number"], int)
    assert segunda["number"] == primera["number"] + 1
    assert primera["created_at"] is not None


# Criterio 2: evento de creación con usuario y fecha.
async def test_crear_orden_registra_el_evento_de_creacion(
    admin: User, cliente: Client, sede: ClientSite, reparacion: WorkType
) -> None:
    async with _client() as client:
        creada = await _crear(client, admin, _pedido(cliente, sede, reparacion))

    async with SessionLocal() as session:
        eventos = list(
            await session.scalars(
                select(WorkOrderEvent).where(
                    WorkOrderEvent.work_order_id == uuid.UUID(str(creada["id"]))
                )
            )
        )
    assert len(eventos) == 1
    evento = eventos[0]
    assert evento.event_type == WorkOrderEventType.created
    assert evento.from_status is None
    assert evento.to_status == OrderStatus.pending
    assert evento.actor_id == admin.id
    assert evento.occurred_at is not None


# Criterio 3: canal a elegir; quién y dónde, opcionales.
@pytest.mark.parametrize("canal", ["whatsapp", "email", "phone", "in_person"])
async def test_cada_canal_es_valido(
    admin: User, cliente: Client, sede: ClientSite, reparacion: WorkType, canal: str
) -> None:
    async with _client() as client:
        creada = await _crear(client, admin, _pedido(cliente, sede, reparacion, channel=canal))

    assert creada["channel"] == canal
    assert creada["requester_name"] is None
    assert creada["requester_area"] is None


async def test_quien_y_donde_se_guardan_recortados(
    admin: User, cliente: Client, sede: ClientSite, reparacion: WorkType
) -> None:
    pedido = _pedido(
        cliente,
        sede,
        reparacion,
        requester_name="  Ana Pérez,  jefa de mantenimiento ",
        requester_area=" Piso 3, ala norte ",
    )
    async with _client() as client:
        creada = await _crear(client, admin, pedido)

    assert creada["requester_name"] == "Ana Pérez, jefa de mantenimiento"
    assert creada["requester_area"] == "Piso 3, ala norte"


async def test_quien_y_donde_vacios_quedan_sin_dato(
    admin: User, cliente: Client, sede: ClientSite, reparacion: WorkType
) -> None:
    pedido = _pedido(cliente, sede, reparacion, requester_name="  ", requester_area="")
    async with _client() as client:
        creada = await _crear(client, admin, pedido)

    assert creada["requester_name"] is None
    assert creada["requester_area"] is None


async def test_canal_inexistente_se_rechaza(
    admin: User, cliente: Client, sede: ClientSite, reparacion: WorkType
) -> None:
    async with _client() as client:
        response = await client.post(
            ORDERS_URL,
            json=_pedido(cliente, sede, reparacion, channel="fax"),
            headers=_auth(admin),
        )

    assert response.status_code == 422


# Criterio 6: los obligatorios faltantes se informan con 422.
async def test_faltantes_se_indican(admin: User) -> None:
    async with _client() as client:
        response = await client.post(ORDERS_URL, json={}, headers=_auth(admin))

    assert response.status_code == 422
    assert _faltantes(response) == {
        "client_id",
        "client_site_id",
        "work_type_id",
        "channel",
        "description",
    }


async def test_descripcion_en_blanco_se_rechaza(
    admin: User, cliente: Client, sede: ClientSite, reparacion: WorkType
) -> None:
    async with _client() as client:
        response = await client.post(
            ORDERS_URL,
            json=_pedido(cliente, sede, reparacion, description="   "),
            headers=_auth(admin),
        )

    assert response.status_code == 422
    assert _faltantes(response) == {"description"}


@pytest.mark.parametrize(("campo", "valor"), [("number", 99), ("status", "done")])
async def test_numero_y_estado_no_se_mandan(
    admin: User,
    cliente: Client,
    sede: ClientSite,
    reparacion: WorkType,
    campo: str,
    valor: object,
) -> None:
    async with _client() as client:
        response = await client.post(
            ORDERS_URL,
            json=_pedido(cliente, sede, reparacion, **{campo: valor}),
            headers=_auth(admin),
        )

    assert response.status_code == 422


# Criterio 7: domicilio ajeno o inactivo, o tipo inactivo, da 422.
async def test_domicilio_de_otro_cliente_se_rechaza(
    admin: User, cliente: Client, reparacion: WorkType
) -> None:
    otro = Client(number="5", name="Otro Cliente")
    await _seed([otro])
    sede_otro = ClientSite(client_id=otro.id, address="Calle 3")
    await _seed([sede_otro])

    async with _client() as client:
        response = await client.post(
            ORDERS_URL, json=_pedido(cliente, sede_otro, reparacion), headers=_auth(admin)
        )

    assert response.status_code == 422
    assert _code(response) == "site_of_another_client"


async def test_domicilio_inactivo_se_rechaza(
    admin: User, cliente: Client, reparacion: WorkType
) -> None:
    inactiva = ClientSite(client_id=cliente.id, address="Calle 9", is_active=False)
    await _seed([inactiva])

    async with _client() as client:
        response = await client.post(
            ORDERS_URL, json=_pedido(cliente, inactiva, reparacion), headers=_auth(admin)
        )

    assert response.status_code == 422
    assert _code(response) == "site_inactive"


async def test_tipo_de_trabajo_inactivo_se_rechaza(
    admin: User, cliente: Client, sede: ClientSite
) -> None:
    viejo = WorkType(name="Tipo viejo", is_active=False)
    await _seed([viejo])

    async with _client() as client:
        response = await client.post(
            ORDERS_URL, json=_pedido(cliente, sede, viejo), headers=_auth(admin)
        )

    assert response.status_code == 422
    assert _code(response) == "work_type_inactive"


@pytest.mark.parametrize(
    ("campo", "codigo"),
    [
        ("client_id", "client_not_found"),
        ("client_site_id", "site_not_found"),
        ("work_type_id", "work_type_not_found"),
    ],
)
async def test_inexistentes_dan_404(
    admin: User,
    cliente: Client,
    sede: ClientSite,
    reparacion: WorkType,
    campo: str,
    codigo: str,
) -> None:
    pedido = _pedido(cliente, sede, reparacion, **{campo: str(uuid.uuid4())})
    async with _client() as client:
        response = await client.post(ORDERS_URL, json=pedido, headers=_auth(admin))

    assert response.status_code == 404
    assert _code(response) == codigo


async def test_un_rechazo_no_deja_orden_ni_evento(
    admin: User, cliente: Client, sede: ClientSite
) -> None:
    viejo = WorkType(name="Tipo viejo", is_active=False)
    await _seed([viejo])

    async with _client() as client:
        await client.post(ORDERS_URL, json=_pedido(cliente, sede, viejo), headers=_auth(admin))

    async with SessionLocal() as session:
        assert list(await session.scalars(select(WorkOrder))) == []
        assert list(await session.scalars(select(WorkOrderEvent))) == []


# Criterio 8: listado de pendientes, de la más vieja a la más nueva.
async def test_listado_de_pendientes(
    admin: User, cliente: Client, sede: ClientSite, reparacion: WorkType
) -> None:
    async with _client() as client:
        vieja = await _crear(client, admin, _pedido(cliente, sede, reparacion))
        nueva = await _crear(client, admin, _pedido(cliente, sede, reparacion))
        response = await client.get(PENDING_URL, headers=_auth(admin))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 2
    assert [item["id"] for item in body["items"]] == [vieja["id"], nueva["id"]]
    item = body["items"][0]
    assert item["number"] == vieja["number"]
    assert item["client_name"] == "Sanatorio Ficticio"
    assert item["site_label"] == "Central"
    assert item["site_address"] == "Calle 1"
    assert item["work_type_name"] == "Reparación"
    assert item["created_at"] == vieja["created_at"]


async def test_listado_no_incluye_otros_estados(
    admin: User, cliente: Client, sede: ClientSite, reparacion: WorkType
) -> None:
    asignada = make_work_order(client_site=sede, work_type=reparacion, status=OrderStatus.assigned)
    await _seed([asignada])

    async with _client() as client:
        response = await client.get(PENDING_URL, headers=_auth(admin))

    assert response.json()["items"] == []
    assert response.json()["total"] == 0


async def test_listado_paginado(
    admin: User, cliente: Client, sede: ClientSite, reparacion: WorkType
) -> None:
    async with _client() as client:
        creadas = [
            await _crear(client, admin, _pedido(cliente, sede, reparacion)) for _ in range(3)
        ]
        response = await client.get(f"{PENDING_URL}&limit=2&offset=1", headers=_auth(admin))

    body = response.json()
    assert body["total"] == 3
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert [item["id"] for item in body["items"]] == [creadas[1]["id"], creadas[2]["id"]]


async def test_listado_solo_admite_pendientes(admin: User) -> None:
    async with _client() as client:
        sin_filtro = await client.get(ORDERS_URL, headers=_auth(admin))
        otro = await client.get(f"{ORDERS_URL}?status=done", headers=_auth(admin))

    assert sin_filtro.status_code == 422
    assert otro.status_code == 422


# Criterio 9: técnico y dirección reciben 403.
@pytest.mark.parametrize("rol", [UserRole.technician, UserRole.owner])
async def test_tecnico_y_direccion_no_crean_ni_listan(
    schema: None,
    cliente: Client,
    sede: ClientSite,
    reparacion: WorkType,
    rol: UserRole,
) -> None:
    usuario = make_user(email=f"{rol.value}@ot-demo.com", role=rol)
    await _seed([usuario])

    async with _client() as client:
        crear = await client.post(
            ORDERS_URL, json=_pedido(cliente, sede, reparacion), headers=_auth(usuario)
        )
        listar = await client.get(PENDING_URL, headers=_auth(usuario))

    assert crear.status_code == 403
    assert listar.status_code == 403
