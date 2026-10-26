import uuid
from collections.abc import AsyncGenerator, Sequence
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import text

from app.core.security import create_access_token
from app.db.models.catalog import EquipmentType, WorkType
from app.db.models.client import Client, ClientContact, ClientSite
from app.db.models.crew import Crew
from app.db.models.equipment import Equipment
from app.db.models.user import User, UserRole
from app.db.models.work_order import WorkOrder, WorkOrderAssignment, WorkOrderEvent
from app.db.session import SessionLocal, engine
from app.domain.work_order import OrderStatus
from app.main import app
from tests.factories import make_user, make_work_order

# E05-01: la escuadrilla ve en el celular sus órdenes Asignada y En curso (D-013).

TABLES = [
    User.__table__,
    Crew.__table__,
    Client.__table__,
    ClientSite.__table__,
    ClientContact.__table__,
    EquipmentType.__table__,
    Equipment.__table__,
    WorkType.__table__,
    WorkOrder.__table__,
    WorkOrderEvent.__table__,
    WorkOrderAssignment.__table__,
]
URL = "/tech/orders"
HOY = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).date()


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
async def celular(schema: None) -> User:
    user = make_user(email="esc1@ot-demo.com", role=UserRole.technician, full_name="Celular 1")
    await _seed([user])
    return user


@pytest.fixture
async def escuadrilla(celular: User) -> Crew:
    item = Crew(name="Escuadrilla 1", app_user_id=celular.id)
    await _seed([item])
    return item


@pytest.fixture
async def otra_escuadrilla(schema: None) -> Crew:
    item = Crew(name="Escuadrilla 2")
    await _seed([item])
    return item


@pytest.fixture
async def sede(schema: None) -> ClientSite:
    cliente = Client(id=uuid.uuid4(), number="10642", name="Sanatorio Ficticio")
    await _seed([cliente])
    item = ClientSite(
        client_id=cliente.id, label="Central", address="Calle 1", reference="Portón verde"
    )
    await _seed([item])
    await _seed(
        [
            ClientContact(
                client_id=cliente.id,
                client_site_id=item.id,
                name="Marta Ficticia",
                phone="3850000000",
                email="marta@ficticio.com",
            )
        ]
    )
    return item


@pytest.fixture
async def reparacion(schema: None) -> WorkType:
    item = WorkType(name="Reparación")
    await _seed([item])
    return item


async def _orden(
    sede: ClientSite,
    tipo: WorkType,
    crew: Crew | None,
    fecha: date = HOY,
    status: OrderStatus = OrderStatus.assigned,
    *,
    unassigned: bool = False,
    equipment: Equipment | None = None,
) -> WorkOrder:
    item = make_work_order(client_site=sede, work_type=tipo, status=status)
    item.description = "Cámara no enfría"
    item.requester_name = "Encargado Ficticio"
    item.requester_area = "Planta baja"
    if equipment is not None:
        item.equipment_id = equipment.id
    await _seed([item])
    if crew is not None:
        await _seed(
            [
                WorkOrderAssignment(
                    work_order_id=item.id,
                    crew_id=crew.id,
                    scheduled_for=fecha,
                    unassigned_at=datetime.now(ZoneInfo("UTC")) if unassigned else None,
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


async def _get(user: User) -> Response:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(URL, headers=_auth(user))


def _numeros(response: Response) -> list[int]:
    return [o["number"] for o in response.json()["orders"]]


# Criterio 1: solo Asignada y En curso de mi escuadrilla, por fecha prevista y número.
async def test_ve_solo_las_abiertas_de_su_escuadrilla_ordenadas(
    celular: User,
    escuadrilla: Crew,
    otra_escuadrilla: Crew,
    sede: ClientSite,
    reparacion: WorkType,
) -> None:
    manana = await _orden(sede, reparacion, escuadrilla, HOY + timedelta(days=1))
    hoy_b = await _orden(sede, reparacion, escuadrilla, HOY, OrderStatus.in_progress)
    hoy_a = await _orden(sede, reparacion, escuadrilla, HOY)
    await _orden(sede, reparacion, otra_escuadrilla, HOY)
    await _orden(sede, reparacion, escuadrilla, HOY, OrderStatus.done)
    await _orden(sede, reparacion, None, status=OrderStatus.pending)

    response = await _get(celular)

    assert response.status_code == 200
    body = response.json()
    assert body["crew"] == {"name": "Escuadrilla 1"}
    assert _numeros(response) == sorted([hoy_a.number, hoy_b.number]) + [manana.number]


# Criterio 2: lo que necesita la tarjeta.
async def test_cada_orden_trae_lo_de_la_tarjeta(
    celular: User, escuadrilla: Crew, sede: ClientSite, reparacion: WorkType
) -> None:
    split = EquipmentType(name="Aire acondicionado")
    await _seed([split])
    equipo = Equipment(
        client_site_id=sede.id,
        equipment_type_id=split.id,
        internal_code="EA1064201",
        location_note="Habitación 12",
        brand="Marca Ficticia",
        model="X1",
    )
    await _seed([equipo])
    con_equipo = await _orden(sede, reparacion, escuadrilla, equipment=equipo)
    sin_equipo = await _orden(sede, reparacion, escuadrilla, HOY + timedelta(days=2))

    orders = (await _get(celular)).json()["orders"]

    primera, segunda = orders
    assert primera["id"] == str(con_equipo.id)
    assert primera["status"] == "assigned"
    assert primera["work_type_name"] == "Reparación"
    assert primera["description"] == "Cámara no enfría"
    assert primera["client_name"] == "Sanatorio Ficticio"
    assert primera["scheduled_for"] == HOY.isoformat()
    assert primera["site"]["address"] == "Calle 1"
    assert primera["site"]["reference"] == "Portón verde"
    assert primera["site"]["contact_names"] == ["Marta Ficticia"]
    assert "maps" in primera["site"]["map_url"]
    assert primera["equipment"] == {
        "location_note": "Habitación 12",
        "equipment_type_name": "Aire acondicionado",
        "brand": "Marca Ficticia",
        "model": "X1",
    }
    assert segunda["id"] == str(sin_equipo.id)
    assert segunda["equipment"] is None


# Criterio 3: el celular calcula "Hoy" y "Vencida" con el día de Argentina.
async def test_informa_el_dia_de_hoy_en_argentina(celular: User, escuadrilla: Crew) -> None:
    body = (await _get(celular)).json()
    assert body["today"] == HOY.isoformat()


# Criterio 3: una vencida sigue apareciendo (se marca en el celular).
async def test_una_orden_vencida_sigue_en_la_lista(
    celular: User, escuadrilla: Crew, sede: ClientSite, reparacion: WorkType
) -> None:
    vencida = await _orden(sede, reparacion, escuadrilla, HOY - timedelta(days=3))
    assert _numeros(await _get(celular)) == [vencida.number]


# Criterio 4: desasignada o cancelada deja de verse.
async def test_desasignada_o_cancelada_no_aparece(
    celular: User, escuadrilla: Crew, sede: ClientSite, reparacion: WorkType
) -> None:
    await _orden(sede, reparacion, escuadrilla, unassigned=True)
    await _orden(sede, reparacion, escuadrilla, status=OrderStatus.cancelled)
    vigente = await _orden(sede, reparacion, escuadrilla)

    assert _numeros(await _get(celular)) == [vigente.number]


# Criterio 5: sin quién pidió, canal, teléfonos ni mails.
async def test_no_expone_datos_que_el_tecnico_no_ve(
    celular: User, escuadrilla: Crew, sede: ClientSite, reparacion: WorkType
) -> None:
    await _orden(sede, reparacion, escuadrilla)

    response = await _get(celular)

    claves = _claves(response.json())
    assert not claves & {"requester_name", "channel", "phone", "email", "price", "history"}
    assert "Encargado Ficticio" not in response.text
    assert "3850000000" not in response.text
    assert "marta@ficticio.com" not in response.text


def _claves(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in _claves(v)}
    if isinstance(value, list):
        return {k for v in value for k in _claves(v)}
    return set()


# Criterio 6: escuadrilla sin órdenes.
async def test_escuadrilla_sin_ordenes_recibe_lista_vacia(celular: User, escuadrilla: Crew) -> None:
    body = (await _get(celular)).json()
    assert body["crew"] == {"name": "Escuadrilla 1"}
    assert body["orders"] == []


# Criterio 7: usuario técnico sin escuadrilla.
async def test_usuario_sin_escuadrilla_no_ve_ordenes(celular: User) -> None:
    response = await _get(celular)
    assert response.status_code == 200
    assert response.json()["crew"] is None
    assert response.json()["orders"] == []


# Criterio 7: una escuadrilla inactiva cuenta como sin escuadrilla.
async def test_escuadrilla_inactiva_cuenta_como_sin_escuadrilla(
    celular: User, escuadrilla: Crew, sede: ClientSite, reparacion: WorkType
) -> None:
    await _orden(sede, reparacion, escuadrilla)
    async with SessionLocal() as session:
        await session.execute(
            text("UPDATE crew SET is_active = false WHERE id = :id"), {"id": escuadrilla.id}
        )
        await session.commit()

    body = (await _get(celular)).json()

    assert body["crew"] is None
    assert body["orders"] == []


# Criterio 8: administración y dirección reciben 403.
@pytest.mark.parametrize("role", [UserRole.admin, UserRole.owner])
async def test_otros_roles_reciben_403(schema: None, role: UserRole) -> None:
    user = make_user(email=f"{role.value}@ot-demo.com", role=role)
    await _seed([user])
    assert (await _get(user)).status_code == 403


async def test_sin_sesion_recibe_401(schema: None) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get(URL)).status_code == 401
