import uuid
from collections.abc import AsyncGenerator, Sequence
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select, text

from app.core.security import create_access_token
from app.db.models.catalog import EquipmentType, Failure, Repair, WorkType
from app.db.models.client import Client, ClientSite
from app.db.models.crew import Crew
from app.db.models.equipment import Equipment
from app.db.models.user import User, UserRole
from app.db.models.work_order import (
    WorkOrder,
    WorkOrderAssignment,
    WorkOrderCancellation,
    WorkOrderClosure,
    WorkOrderEvent,
)
from app.db.session import SessionLocal, engine
from app.domain.work_order import OrderStatus, WorkOrderEventType
from app.main import app
from tests.factories import make_user, make_work_order

# E04-12: el equipo de la orden, opcional, uno por orden, cambiable hasta que se inicie.

TABLES = [
    User.__table__,
    Client.__table__,
    ClientSite.__table__,
    EquipmentType.__table__,
    Equipment.__table__,
    WorkType.__table__,
    Failure.__table__,
    Repair.__table__,
    Crew.__table__,
    WorkOrder.__table__,
    WorkOrderEvent.__table__,
    WorkOrderAssignment.__table__,
    WorkOrderClosure.__table__,
    WorkOrderCancellation.__table__,
]
ORDERS_URL = "/admin/orders"


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
            "cancel_reason",
            "closure_outcome",
            "equipment_condition",
            "not_done_reason",
            "no_signature_reason",
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
async def otra_sede(cliente: Client) -> ClientSite:
    item = ClientSite(client_id=cliente.id, label="Depósito", address="Calle 2")
    await _seed([item])
    return item


@pytest.fixture
async def reparacion(schema: None) -> WorkType:
    item = WorkType(name="Reparación")
    await _seed([item])
    return item


@pytest.fixture
async def aire(schema: None) -> EquipmentType:
    item = EquipmentType(name="Aire acondicionado")
    await _seed([item])
    return item


async def _equipo(
    sede: ClientSite, tipo: EquipmentType, codigo: str, *, baja: bool = False
) -> Equipment:
    item = Equipment(
        client_site_id=sede.id,
        equipment_type_id=tipo.id,
        internal_code=codigo,
        location_note=f"Ubicación {codigo}",
        deleted_at=datetime.now(UTC) if baja else None,
    )
    await _seed([item])
    return item


async def _orden(
    sede: ClientSite, tipo: WorkType, status: OrderStatus = OrderStatus.pending
) -> WorkOrder:
    item = make_work_order(client_site=sede, work_type=tipo, status=status)
    await _seed([item])
    await _seed(
        [
            WorkOrderEvent(
                work_order_id=item.id, event_type=WorkOrderEventType.created, to_status=status
            )
        ]
    )
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
        "description": "No enfría",
        **extra,
    }


async def _cambiar(user: User, orden: WorkOrder, equipment_id: uuid.UUID | None) -> Response:
    async with _client() as client:
        return await client.put(
            f"{ORDERS_URL}/{orden.id}/equipment",
            json={"equipment_id": str(equipment_id) if equipment_id else None},
            headers=_auth(user),
        )


async def _equipo_de(orden_id: uuid.UUID | str) -> uuid.UUID | None:
    async with SessionLocal() as session:
        return await session.scalar(
            select(WorkOrder.equipment_id).where(WorkOrder.id == uuid.UUID(str(orden_id)))
        )


def _error(response: Response) -> tuple[str, str | None]:
    detail = response.json()["detail"]
    return detail["code"], detail.get("field")


# Criterio 1: al crear, un equipo del domicilio elegido.
async def test_crear_orden_con_equipo_del_domicilio(
    admin: User, cliente: Client, sede: ClientSite, reparacion: WorkType, aire: EquipmentType
) -> None:
    equipo = await _equipo(sede, aire, "EA1")

    async with _client() as client:
        response = await client.post(
            ORDERS_URL,
            json=_pedido(cliente, sede, reparacion, equipment_id=str(equipo.id)),
            headers=_auth(admin),
        )

    assert response.status_code == 201
    assert response.json()["equipment_id"] == str(equipo.id)
    assert await _equipo_de(response.json()["id"]) == equipo.id


# Criterio 2: el equipo es opcional.
async def test_crear_orden_sin_equipo(
    admin: User, cliente: Client, sede: ClientSite, reparacion: WorkType
) -> None:
    async with _client() as client:
        response = await client.post(
            ORDERS_URL, json=_pedido(cliente, sede, reparacion), headers=_auth(admin)
        )

    assert response.status_code == 201
    assert response.json()["equipment_id"] is None


# Criterio 4: de otro domicilio, de otro cliente, dado de baja o inexistente.
async def test_crear_orden_rechaza_equipo_que_no_es_del_domicilio(
    admin: User,
    cliente: Client,
    sede: ClientSite,
    otra_sede: ClientSite,
    reparacion: WorkType,
    aire: EquipmentType,
) -> None:
    otro_cliente = Client(number="5", name="Otro Cliente")
    await _seed([otro_cliente])
    sede_ajena = ClientSite(client_id=otro_cliente.id, address="Calle 3")
    await _seed([sede_ajena])
    equipos = [
        await _equipo(otra_sede, aire, "EA2"),
        await _equipo(sede_ajena, aire, "EA3"),
        await _equipo(sede, aire, "EA4", baja=True),
    ]

    async with _client() as client:
        for equipment_id in [*(e.id for e in equipos), uuid.uuid4()]:
            response = await client.post(
                ORDERS_URL,
                json=_pedido(cliente, sede, reparacion, equipment_id=str(equipment_id)),
                headers=_auth(admin),
            )
            assert response.status_code == 422
            assert _error(response) == ("equipment_not_available", "equipment_id")

    async with SessionLocal() as session:
        assert await session.scalar(select(WorkOrder.id)) is None


# Criterio 3: agregar, cambiar y sacar el equipo en Pendiente y Asignada.
@pytest.mark.parametrize("status", [OrderStatus.pending, OrderStatus.assigned])
async def test_cambiar_equipo_hasta_que_se_inicie(
    admin: User, sede: ClientSite, reparacion: WorkType, aire: EquipmentType, status: OrderStatus
) -> None:
    orden = await _orden(sede, reparacion, status)
    primero = await _equipo(sede, aire, "EA1")
    segundo = await _equipo(sede, aire, "EA2")

    agregar = await _cambiar(admin, orden, primero.id)
    assert agregar.status_code == 200
    assert agregar.json()["equipment_id"] == str(primero.id)
    assert (await _cambiar(admin, orden, segundo.id)).status_code == 200
    assert await _equipo_de(orden.id) == segundo.id
    assert (await _cambiar(admin, orden, None)).status_code == 200
    assert await _equipo_de(orden.id) is None


# Criterio 3: cada cambio queda en la línea de tiempo, sin cambiar el estado.
async def test_cambiar_equipo_registra_el_evento(
    admin: User, sede: ClientSite, reparacion: WorkType, aire: EquipmentType
) -> None:
    orden = await _orden(sede, reparacion)
    primero = await _equipo(sede, aire, "EA1")
    segundo = await _equipo(sede, aire, "EA2")

    await _cambiar(admin, orden, primero.id)
    await _cambiar(admin, orden, segundo.id)
    await _cambiar(admin, orden, None)
    # Elegir el mismo que ya tiene no es un cambio.
    await _cambiar(admin, orden, None)

    async with SessionLocal() as session:
        eventos = (
            await session.scalars(
                select(WorkOrderEvent)
                .where(
                    WorkOrderEvent.work_order_id == orden.id,
                    WorkOrderEvent.event_type == WorkOrderEventType.equipment_changed,
                )
                .order_by(WorkOrderEvent.occurred_at)
            )
        ).all()
    assert [(e.note, e.from_status, e.to_status, e.actor_id) for e in eventos] == [
        ("Equipo: sin equipo -> EA1", None, None, admin.id),
        ("Equipo: EA1 -> EA2", None, None, admin.id),
        ("Equipo: EA2 -> sin equipo", None, None, admin.id),
    ]


# Criterio 3: iniciada, terminada o cancelada ya no se cambia.
@pytest.mark.parametrize(
    "status", [OrderStatus.in_progress, OrderStatus.done, OrderStatus.cancelled]
)
async def test_no_se_cambia_el_equipo_despues_de_iniciar(
    admin: User, sede: ClientSite, reparacion: WorkType, aire: EquipmentType, status: OrderStatus
) -> None:
    orden = await _orden(sede, reparacion, status)
    equipo = await _equipo(sede, aire, "EA1")

    response = await _cambiar(admin, orden, equipo.id)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "order_not_editable"
    assert await _equipo_de(orden.id) is None


# Criterio 4: al cambiar, la misma validación que al crear.
async def test_cambiar_rechaza_equipo_de_otro_domicilio(
    admin: User,
    sede: ClientSite,
    otra_sede: ClientSite,
    reparacion: WorkType,
    aire: EquipmentType,
) -> None:
    orden = await _orden(sede, reparacion)
    ajeno = await _equipo(otra_sede, aire, "EA2")

    response = await _cambiar(admin, orden, ajeno.id)

    assert response.status_code == 422
    assert _error(response) == ("equipment_not_available", "equipment_id")


async def test_cambiar_equipo_de_orden_inexistente_da_404(admin: User) -> None:
    response = await _cambiar(admin, WorkOrder(id=uuid.uuid4()), None)
    assert response.status_code == 404


# Criterio 5: el listado de la oficina muestra el equipo.
async def test_listado_muestra_el_equipo(
    admin: User, sede: ClientSite, reparacion: WorkType, aire: EquipmentType
) -> None:
    con_equipo = await _orden(sede, reparacion)
    sin_equipo = await _orden(sede, reparacion)
    equipo = await _equipo(sede, aire, "EA1")
    await _cambiar(admin, con_equipo, equipo.id)

    async with _client() as client:
        response = await client.get(f"{ORDERS_URL}?status=pending", headers=_auth(admin))

    por_numero = {item["number"]: item["equipment"] for item in response.json()["items"]}
    assert por_numero[con_equipo.number] == {
        "id": str(equipo.id),
        "internal_code": "EA1",
        "location_note": "Ubicación EA1",
    }
    assert por_numero[sin_equipo.number] is None


# Criterio 7: técnico y dirección no cambian el equipo.
@pytest.mark.parametrize("role", [UserRole.technician, UserRole.owner])
async def test_otros_roles_no_cambian_el_equipo(
    schema: None, sede: ClientSite, reparacion: WorkType, role: UserRole
) -> None:
    user = make_user(email=f"{role.value}@ot-demo.com", role=role)
    await _seed([user])
    orden = await _orden(sede, reparacion)

    assert (await _cambiar(user, orden, None)).status_code == 403
