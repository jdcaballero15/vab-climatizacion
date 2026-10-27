import uuid
from collections.abc import AsyncGenerator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import text

from app.core.security import create_access_token
from app.db.models.catalog import EquipmentType, Failure, Repair, Task, WorkType
from app.db.models.client import Client, ClientContact, ClientSite
from app.db.models.crew import Crew, FieldTechnician
from app.db.models.equipment import Equipment
from app.db.models.user import User, UserRole
from app.db.models.work_order import (
    WorkOrder,
    WorkOrderAssignment,
    WorkOrderCancellation,
    WorkOrderClosure,
    WorkOrderClosureTask,
    WorkOrderClosureTechnician,
    WorkOrderEvent,
)
from app.db.session import SessionLocal, engine
from app.domain.work_order import (
    ClosureOutcome,
    EquipmentCondition,
    NotDoneReason,
    OrderStatus,
    WorkOrderEventType,
)
from app.main import app
from tests.factories import make_user, make_work_order

# E04-08, criterio 1: administración ve las terminadas y lo que cargó la escuadrilla.
TABLES = [
    User.__table__,
    Crew.__table__,
    FieldTechnician.__table__,
    Client.__table__,
    ClientSite.__table__,
    ClientContact.__table__,
    EquipmentType.__table__,
    Equipment.__table__,
    WorkType.__table__,
    Task.__table__,
    Failure.__table__,
    Repair.__table__,
    WorkOrder.__table__,
    WorkOrderEvent.__table__,
    WorkOrderAssignment.__table__,
    WorkOrderClosure.__table__,
    WorkOrderClosureTechnician.__table__,
    WorkOrderClosureTask.__table__,
    WorkOrderCancellation.__table__,
]
ORDERS_URL = "/admin/orders"
AYER = datetime.now(UTC) - timedelta(days=1)


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
            "closure_outcome",
            "equipment_condition",
            "not_done_reason",
            "cancel_reason",
        ):
            await conn.execute(text(f"DROP TYPE IF EXISTS {enum_type}"))
        await conn.execute(text("DROP SEQUENCE IF EXISTS work_order_number_seq"))


@dataclass
class Mundo:
    admin: User
    celular: User
    escuadrilla: Crew
    sede: ClientSite
    reparacion: WorkType


@pytest.fixture
async def mundo(schema: None) -> Mundo:
    admin = make_user(email="admin@ot-demo.com", role=UserRole.admin, full_name="Admin Ficticia")
    celular = make_user(email="esc1@ot-demo.com", role=UserRole.technician, full_name="Celular 1")
    await _seed([admin, celular])
    escuadrilla = Crew(name="Escuadrilla 1", app_user_id=celular.id)
    cliente = Client(id=uuid.uuid4(), number="10642", name="Sanatorio Ficticio")
    reparacion = WorkType(name="Reparación")
    await _seed([escuadrilla, cliente, reparacion])
    sede = ClientSite(client_id=cliente.id, label="Central", address="Calle 1")
    await _seed([sede])
    return Mundo(
        admin=admin, celular=celular, escuadrilla=escuadrilla, sede=sede, reparacion=reparacion
    )


async def _seed(items: Sequence[object]) -> None:
    async with SessionLocal() as session:
        session.add_all(list(items))
        await session.commit()


async def _orden(m: Mundo, status: OrderStatus) -> WorkOrder:
    """Orden con su evento de creación y una asignación de la escuadrilla de antes de ayer."""
    item = make_work_order(client_site=m.sede, work_type=m.reparacion, status=status)
    await _seed([item])
    await _seed(
        [
            WorkOrderEvent(
                work_order_id=item.id,
                event_type=WorkOrderEventType.created,
                to_status=OrderStatus.pending,
            ),
            WorkOrderAssignment(
                work_order_id=item.id,
                crew_id=m.escuadrilla.id,
                scheduled_for=AYER.date(),
                assigned_at=AYER - timedelta(days=1),
            ),
        ]
    )
    return item


async def _cierre(m: Mundo, orden: WorkOrder, closed_at: datetime = AYER, **values: Any) -> None:
    await _seed(
        [
            WorkOrderClosure(
                work_order_id=orden.id,
                closed_by=m.celular.id,
                closed_at=closed_at,
                idempotency_key=uuid.uuid4(),
                **({"outcome": ClosureOutcome.done} | values),
            )
        ]
    )


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


async def _get(user: User, url: str) -> Response:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(url, headers=_auth(user))


# ---- Listado de terminadas ----


async def test_lista_las_terminadas_con_escuadrilla_y_fecha_de_cierre(mundo: Mundo) -> None:
    m = mundo
    vieja = await _orden(m, OrderStatus.done)
    nueva = await _orden(m, OrderStatus.done)
    await _orden(m, OrderStatus.pending)
    await _cierre(m, vieja, closed_at=AYER - timedelta(hours=5))
    await _cierre(m, nueva)

    response = await _get(m.admin, f"{ORDERS_URL}?status=done")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    # La última terminada primero.
    assert [item["number"] for item in body["items"]] == [nueva.number, vieja.number]
    item = body["items"][0]
    assert item["status"] == "done"
    assert item["completed"]["crew_name"] == "Escuadrilla 1"
    assert datetime.fromisoformat(item["completed"]["closed_at"]) == AYER
    assert (item["returned"], item["assignment"], item["cancellation"]) == (None, None, None)


async def test_las_demas_no_traen_terminada(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m, OrderStatus.pending)
    await _cierre(m, orden, outcome=ClosureOutcome.needs_revisit, observation="Falta repuesto")

    [item] = (await _get(m.admin, f"{ORDERS_URL}?status=pending")).json()["items"]

    assert item["completed"] is None
    assert item["returned"]["outcome"] == "needs_revisit"


# ---- Lo que cargó la escuadrilla ----


async def test_cierre_con_todo_lo_que_cargo_la_escuadrilla(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m, OrderStatus.done)
    ana = FieldTechnician(full_name="Ana Ficticia")
    beto = FieldTechnician(full_name="Beto Inventado")
    limpieza = Task(work_type_id=m.reparacion.id, name="Limpieza de filtros")
    carga = Task(work_type_id=m.reparacion.id, name="Carga de gas")
    falla = Failure(name="Pérdida de gas")
    await _seed([ana, beto, limpieza, carga, falla])
    await _cierre(
        m,
        orden,
        failure_id=falla.id,
        repair_other_text="Soldadura en la cañería",
        equipment_condition=EquipmentCondition.working_with_notes,
        observation="Revisar en un mes.",
    )
    async with SessionLocal() as session:
        closure_id = (await session.execute(text("select id from work_order_closure"))).scalar()
    await _seed(
        [
            WorkOrderClosureTechnician(closure_id=closure_id, field_technician_id=beto.id),
            WorkOrderClosureTechnician(closure_id=closure_id, field_technician_id=ana.id),
            WorkOrderClosureTask(closure_id=closure_id, task_id=limpieza.id),
            WorkOrderClosureTask(closure_id=closure_id, task_id=carga.id),
        ]
    )

    response = await _get(m.admin, f"{ORDERS_URL}/{orden.id}/closure")

    assert response.status_code == 200
    body = response.json()
    assert datetime.fromisoformat(body.pop("closed_at")) == AYER
    assert body == {
        "outcome": "done",
        "closed_by_name": "Celular 1",
        "crew_name": "Escuadrilla 1",
        "technicians": ["Ana Ficticia", "Beto Inventado"],
        "tasks": ["Carga de gas", "Limpieza de filtros"],
        "failure": "Pérdida de gas",
        "repair": "Soldadura en la cañería",
        "equipment_condition": "working_with_notes",
        "not_done_reason": None,
        "observation": "Revisar en un mes.",
    }


async def test_devuelve_el_ultimo_cierre(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m, OrderStatus.done)
    await _cierre(
        m,
        orden,
        closed_at=AYER - timedelta(hours=3),
        outcome=ClosureOutcome.not_done,
        not_done_reason=NotDoneReason.client_absent,
    )
    await _cierre(m, orden, observation="Segunda visita, resuelta.")

    body = (await _get(m.admin, f"{ORDERS_URL}/{orden.id}/closure")).json()

    assert (body["outcome"], body["observation"]) == ("done", "Segunda visita, resuelta.")


async def test_orden_sin_cierre_da_404(mundo: Mundo) -> None:
    orden = await _orden(mundo, OrderStatus.assigned)

    response = await _get(mundo.admin, f"{ORDERS_URL}/{orden.id}/closure")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "closure_not_found"


async def test_orden_inexistente_da_404(mundo: Mundo) -> None:
    response = await _get(mundo.admin, f"{ORDERS_URL}/{uuid.uuid4()}/closure")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "order_not_found"


async def test_el_tecnico_no_puede_ver_el_cierre_desde_administracion(mundo: Mundo) -> None:
    orden = await _orden(mundo, OrderStatus.done)
    await _cierre(mundo, orden)

    response = await _get(mundo.celular, f"{ORDERS_URL}/{orden.id}/closure")

    assert response.status_code == 403
