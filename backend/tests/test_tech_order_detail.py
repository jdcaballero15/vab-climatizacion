import uuid
from collections.abc import AsyncGenerator, Sequence
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import text

from app.core.security import create_access_token
from app.db.models.catalog import EquipmentType, Task, WorkType
from app.db.models.client import Client, ClientContact, ClientSite
from app.db.models.crew import Crew
from app.db.models.equipment import Equipment
from app.db.models.user import User, UserRole
from app.db.models.work_order import WorkOrder, WorkOrderAssignment, WorkOrderEvent
from app.db.session import SessionLocal, engine
from app.domain.work_order import OrderStatus
from app.main import app
from tests.factories import make_user, make_work_order

# E05-02: la escuadrilla abre el detalle de una de sus órdenes abiertas.

TABLES = [
    User.__table__,
    Crew.__table__,
    Client.__table__,
    ClientSite.__table__,
    ClientContact.__table__,
    EquipmentType.__table__,
    Equipment.__table__,
    WorkType.__table__,
    Task.__table__,
    WorkOrder.__table__,
    WorkOrderEvent.__table__,
    WorkOrderAssignment.__table__,
]
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
    await _seed(
        [
            Task(work_type_id=item.id, name="Probar el funcionamiento"),
            Task(work_type_id=item.id, name="Diagnosticar la falla"),
            Task(work_type_id=item.id, name="Tarea vieja", is_active=False),
        ]
    )
    return item


async def _orden(
    sede: ClientSite,
    tipo: WorkType,
    crew: Crew | None,
    status: OrderStatus = OrderStatus.assigned,
    *,
    unassigned: bool = False,
    equipment: Equipment | None = None,
) -> WorkOrder:
    item = make_work_order(client_site=sede, work_type=tipo, status=status)
    item.description = "Cámara no enfría. Mercadería en riesgo: ir primero."
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
                    scheduled_for=HOY,
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


async def _get(user: User, order_id: object) -> Response:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(f"/tech/orders/{order_id}", headers=_auth(user))


# Criterios 1 a 4: lo necesario para hacer el trabajo.
async def test_detalle_de_una_orden_de_mi_escuadrilla(
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
    orden = await _orden(sede, reparacion, escuadrilla, OrderStatus.in_progress, equipment=equipo)

    response = await _get(celular, orden.id)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(orden.id)
    assert body["number"] == orden.number
    assert body["status"] == "in_progress"
    assert body["work_type_name"] == "Reparación"
    assert body["description"] == "Cámara no enfría. Mercadería en riesgo: ir primero."
    assert body["client_name"] == "Sanatorio Ficticio"
    assert body["scheduled_for"] == HOY.isoformat()
    assert body["today"] == HOY.isoformat()
    assert body["requester_area"] == "Planta baja"
    assert body["site"]["address"] == "Calle 1"
    assert body["site"]["reference"] == "Portón verde"
    assert body["site"]["contact_names"] == ["Marta Ficticia"]
    assert "maps" in body["site"]["map_url"]
    assert body["equipment"] == {
        "location_note": "Habitación 12",
        "equipment_type_name": "Aire acondicionado",
        "brand": "Marca Ficticia",
        "model": "X1",
    }
    # Solo las activas, por nombre (como en administración).
    assert body["tasks"] == ["Diagnosticar la falla", "Probar el funcionamiento"]


# Criterio 3: un tipo de trabajo desactivado no ofrece tareas.
async def test_tipo_de_trabajo_desactivado_no_muestra_tareas(
    celular: User, escuadrilla: Crew, sede: ClientSite, reparacion: WorkType
) -> None:
    orden = await _orden(sede, reparacion, escuadrilla)
    async with SessionLocal() as session:
        await session.execute(
            text("UPDATE work_type SET is_active = false WHERE id = :id"), {"id": reparacion.id}
        )
        await session.commit()

    body = (await _get(celular, orden.id)).json()

    assert body["tasks"] == []


# Criterio 5: sin quién pidió, canal, teléfonos, mails, precios ni historial.
async def test_no_expone_datos_que_el_tecnico_no_ve(
    celular: User, escuadrilla: Crew, sede: ClientSite, reparacion: WorkType
) -> None:
    orden = await _orden(sede, reparacion, escuadrilla)

    response = await _get(celular, orden.id)

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


# Criterio 6: cualquier orden que no sea abierta y de mi escuadrilla da 404.
@pytest.mark.parametrize(
    ("de_otra", "status", "unassigned"),
    [
        (True, OrderStatus.assigned, False),
        (False, OrderStatus.done, False),
        (False, OrderStatus.cancelled, False),
        (False, OrderStatus.assigned, True),
    ],
    ids=["otra-escuadrilla", "terminada", "cancelada", "desasignada"],
)
async def test_orden_que_no_es_abierta_de_mi_escuadrilla_da_404(
    celular: User,
    escuadrilla: Crew,
    otra_escuadrilla: Crew,
    sede: ClientSite,
    reparacion: WorkType,
    de_otra: bool,
    status: OrderStatus,
    unassigned: bool,
) -> None:
    crew = otra_escuadrilla if de_otra else escuadrilla
    orden = await _orden(sede, reparacion, crew, status, unassigned=unassigned)

    response = await _get(celular, orden.id)

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "order_not_found"


async def test_orden_pendiente_sin_asignar_da_404(
    celular: User, escuadrilla: Crew, sede: ClientSite, reparacion: WorkType
) -> None:
    orden = await _orden(sede, reparacion, None, OrderStatus.pending)
    assert (await _get(celular, orden.id)).status_code == 404


async def test_id_inexistente_da_404(celular: User, escuadrilla: Crew) -> None:
    assert (await _get(celular, uuid.uuid4())).status_code == 404


async def test_usuario_sin_escuadrilla_da_404(
    celular: User, otra_escuadrilla: Crew, sede: ClientSite, reparacion: WorkType
) -> None:
    orden = await _orden(sede, reparacion, otra_escuadrilla)
    assert (await _get(celular, orden.id)).status_code == 404


# Criterio 8: administración y dirección reciben 403.
@pytest.mark.parametrize("role", [UserRole.admin, UserRole.owner])
async def test_otros_roles_reciben_403(schema: None, role: UserRole) -> None:
    user = make_user(email=f"{role.value}@ot-demo.com", role=role)
    await _seed([user])
    assert (await _get(user, uuid.uuid4())).status_code == 403
