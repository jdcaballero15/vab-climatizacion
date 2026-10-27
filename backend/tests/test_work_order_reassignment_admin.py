import uuid
from collections.abc import AsyncGenerator, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select, text

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
    NotDoneReason,
    OrderStatus,
    WorkOrderEventType,
)
from app.main import app
from tests.factories import make_user, make_work_order

# E04-04: administración reasigna, desasigna o reprograma una orden.
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
HOY = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).date()
MANANA = HOY + timedelta(days=1)
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
    celular1: User
    celular2: User
    escuadrilla1: Crew
    escuadrilla2: Crew
    inactiva: Crew
    sede: ClientSite
    reparacion: WorkType


@pytest.fixture
async def mundo(schema: None) -> Mundo:
    admin = make_user(email="admin@ot-demo.com", role=UserRole.admin, full_name="Admin Ficticia")
    celular1 = make_user(email="esc1@ot-demo.com", role=UserRole.technician, full_name="Cel 1")
    celular2 = make_user(email="esc2@ot-demo.com", role=UserRole.technician, full_name="Cel 2")
    await _seed([admin, celular1, celular2])
    escuadrilla1 = Crew(name="Escuadrilla 1", app_user_id=celular1.id)
    escuadrilla2 = Crew(name="Escuadrilla 2", app_user_id=celular2.id)
    inactiva = Crew(name="Escuadrilla vieja", is_active=False)
    cliente = Client(id=uuid.uuid4(), number="10642", name="Sanatorio Ficticio")
    reparacion = WorkType(name="Reparación")
    await _seed([escuadrilla1, escuadrilla2, inactiva, cliente, reparacion])
    sede = ClientSite(client_id=cliente.id, label="Central", address="Calle 1")
    await _seed([sede])
    return Mundo(
        admin=admin,
        celular1=celular1,
        celular2=celular2,
        escuadrilla1=escuadrilla1,
        escuadrilla2=escuadrilla2,
        inactiva=inactiva,
        sede=sede,
        reparacion=reparacion,
    )


async def _seed(items: Sequence[object]) -> None:
    async with SessionLocal() as session:
        session.add_all(list(items))
        await session.commit()


async def _orden(m: Mundo, status: OrderStatus) -> WorkOrder:
    """Orden con su evento de creación y, si está Asignada o En curso, en la Escuadrilla 1."""
    item = make_work_order(client_site=m.sede, work_type=m.reparacion, status=status)
    await _seed([item])
    await _seed(
        [
            WorkOrderEvent(
                work_order_id=item.id,
                event_type=WorkOrderEventType.created,
                to_status=OrderStatus.pending,
            )
        ]
    )
    if status in (OrderStatus.assigned, OrderStatus.in_progress):
        await _seed(
            [
                WorkOrderAssignment(
                    work_order_id=item.id, crew_id=m.escuadrilla1.id, scheduled_for=HOY
                )
            ]
        )
    return item


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _post(user: User, url: str, payload: dict[str, Any]) -> Response:
    async with _client() as client:
        return await client.post(url, json=payload, headers=_auth(user))


async def _get(user: User, url: str) -> Response:
    async with _client() as client:
        return await client.get(url, headers=_auth(user))


def _reasignar(crew: Crew, day: date = MANANA, **extra: object) -> dict[str, object]:
    return {"crew_id": str(crew.id), "scheduled_for": day.isoformat(), **extra}


async def _estado(order_id: uuid.UUID) -> OrderStatus:
    async with SessionLocal() as session:
        status = await session.scalar(select(WorkOrder.status).where(WorkOrder.id == order_id))
    assert status is not None
    return status


async def _asignaciones(order_id: uuid.UUID) -> list[WorkOrderAssignment]:
    async with SessionLocal() as session:
        result = await session.scalars(
            select(WorkOrderAssignment)
            .where(WorkOrderAssignment.work_order_id == order_id)
            .order_by(WorkOrderAssignment.assigned_at)
        )
        return list(result)


async def _ultimo_evento(order_id: uuid.UUID) -> WorkOrderEvent:
    async with SessionLocal() as session:
        event = await session.scalar(
            select(WorkOrderEvent)
            .where(WorkOrderEvent.work_order_id == order_id)
            .order_by(WorkOrderEvent.occurred_at.desc())
            .limit(1)
        )
    assert event is not None
    return event


async def _ids_del_celular(user: User) -> list[str]:
    return [o["id"] for o in (await _get(user, "/tech/orders")).json()["orders"]]


# ---- Reasignar (criterios 1 y 2) ----


# Criterio 1: la escuadrilla anterior deja de verla y la nueva la ve Asignada.
async def test_reasignar_una_asignada_cambia_de_escuadrilla(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m, OrderStatus.assigned)

    response = await _post(
        m.admin, f"{ORDERS_URL}/{orden.id}/reassignment", _reasignar(m.escuadrilla2)
    )

    assert response.status_code == 201
    assert response.json()["crew_id"] == str(m.escuadrilla2.id)
    assert response.json()["scheduled_for"] == MANANA.isoformat()
    assert await _estado(orden.id) == OrderStatus.assigned
    vieja, nueva = await _asignaciones(orden.id)
    assert vieja.unassigned_at is not None
    assert (nueva.crew_id, nueva.unassigned_at) == (m.escuadrilla2.id, None)
    assert await _ids_del_celular(m.celular1) == []
    [visible] = (await _get(m.celular2, "/tech/orders")).json()["orders"]
    assert (visible["id"], visible["status"]) == (str(orden.id), "assigned")


# Criterio 2: una En curso le llega a la nueva escuadrilla como Asignada.
async def test_reasignar_una_en_curso_la_deja_asignada(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m, OrderStatus.in_progress)

    response = await _post(
        m.admin, f"{ORDERS_URL}/{orden.id}/reassignment", _reasignar(m.escuadrilla2)
    )

    assert response.status_code == 201
    assert await _estado(orden.id) == OrderStatus.assigned
    assert await _ids_del_celular(m.celular1) == []
    assert await _ids_del_celular(m.celular2) == [str(orden.id)]
    # La escuadrilla anterior ya no la puede cerrar.
    detalle = await _get(m.celular1, f"/tech/orders/{orden.id}")
    assert detalle.status_code == 404


async def test_reasignar_a_la_misma_escuadrilla_otro_dia(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m, OrderStatus.assigned)

    response = await _post(
        m.admin, f"{ORDERS_URL}/{orden.id}/reassignment", _reasignar(m.escuadrilla1)
    )

    assert response.status_code == 201
    assert [a.scheduled_for for a in await _asignaciones(orden.id)] == [HOY, MANANA]


# ---- Desasignar (criterio 3) ----


async def test_desasignar_una_asignada_vuelve_a_pendiente(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m, OrderStatus.assigned)

    response = await _post(m.admin, f"{ORDERS_URL}/{orden.id}/unassignment", {})

    assert response.status_code == 204
    assert await _estado(orden.id) == OrderStatus.pending
    [asignacion] = await _asignaciones(orden.id)
    assert asignacion.unassigned_at is not None
    assert await _ids_del_celular(m.celular1) == []
    [item] = (await _get(m.admin, f"{ORDERS_URL}?status=pending")).json()["items"]
    assert (item["id"], item["assignment"]) == (str(orden.id), None)


async def test_no_se_desasigna_una_en_curso(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m, OrderStatus.in_progress)

    response = await _post(m.admin, f"{ORDERS_URL}/{orden.id}/unassignment", {})

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "invalid_transition"
    assert await _estado(orden.id) == OrderStatus.in_progress


# ---- Reprogramar (criterio 4) ----


async def test_reprogramar_una_que_volvio_conserva_el_cierre(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m, OrderStatus.pending)
    await _seed(
        [
            WorkOrderAssignment(
                work_order_id=orden.id,
                crew_id=m.escuadrilla1.id,
                scheduled_for=HOY,
                assigned_at=datetime.now(ZoneInfo("UTC")) - timedelta(hours=5),
                unassigned_at=datetime.now(ZoneInfo("UTC")) - timedelta(hours=1),
            ),
            WorkOrderClosure(
                work_order_id=orden.id,
                closed_by=m.celular1.id,
                closed_at=datetime.now(ZoneInfo("UTC")) - timedelta(hours=1),
                outcome=ClosureOutcome.not_done,
                not_done_reason=NotDoneReason.client_absent,
                idempotency_key=uuid.uuid4(),
            ),
        ]
    )
    # El listado trae la escuadrilla para preelegirla.
    [item] = (await _get(m.admin, f"{ORDERS_URL}?status=pending")).json()["items"]
    assert item["returned"]["crew_id"] == str(m.escuadrilla1.id)

    response = await _post(
        m.admin,
        f"{ORDERS_URL}/{orden.id}/assignment",
        _reasignar(m.escuadrilla1, reason="El cliente avisó que mañana está"),
    )

    assert response.status_code == 201
    assert await _estado(orden.id) == OrderStatus.assigned
    async with SessionLocal() as session:
        cierres = list(await session.scalars(select(WorkOrderClosure)))
    assert len(cierres) == 1
    evento = await _ultimo_evento(orden.id)
    assert evento.note is not None
    assert evento.note.endswith("Motivo: El cliente avisó que mañana está.")


# ---- Evento con motivo (criterio 5) ----


async def test_reasignar_deja_el_evento_con_el_motivo(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m, OrderStatus.in_progress)

    await _post(
        m.admin,
        f"{ORDERS_URL}/{orden.id}/reassignment",
        _reasignar(m.escuadrilla2, reason="  La Escuadrilla 1 tuvo un problema  "),
    )

    evento = await _ultimo_evento(orden.id)
    assert evento.event_type == WorkOrderEventType.reassigned
    assert (evento.from_status, evento.to_status) == (
        OrderStatus.in_progress,
        OrderStatus.assigned,
    )
    assert evento.actor_id == m.admin.id
    assert evento.note == (
        f"Escuadrilla: Escuadrilla 2. Fecha prevista: {MANANA.strftime('%d/%m/%Y')}. "
        "Motivo: La Escuadrilla 1 tuvo un problema."
    )


async def test_desasignar_deja_el_evento_con_el_motivo_opcional(mundo: Mundo) -> None:
    m = mundo
    con_motivo = await _orden(m, OrderStatus.assigned)
    sin_motivo = await _orden(m, OrderStatus.assigned)

    await _post(m.admin, f"{ORDERS_URL}/{con_motivo.id}/unassignment", {"reason": "Se reprograma"})
    await _post(m.admin, f"{ORDERS_URL}/{sin_motivo.id}/unassignment", {"reason": "   "})

    evento = await _ultimo_evento(con_motivo.id)
    assert (evento.event_type, evento.note) == (
        WorkOrderEventType.unassigned,
        "Motivo: Se reprograma.",
    )
    assert (await _ultimo_evento(sin_motivo.id)).note is None


# ---- Rechazos (criterio 6) ----


async def test_misma_escuadrilla_y_fecha_se_rechaza_con_el_campo(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m, OrderStatus.assigned)

    response = await _post(
        m.admin, f"{ORDERS_URL}/{orden.id}/reassignment", _reasignar(m.escuadrilla1, HOY)
    )

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "code": "same_assignment",
        "message": "Ya está asignada a esa escuadrilla para ese día.",
        "field": "crew_id",
    }
    assert len(await _asignaciones(orden.id)) == 1


async def test_escuadrilla_inactiva_se_rechaza_con_el_campo(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m, OrderStatus.assigned)

    response = await _post(m.admin, f"{ORDERS_URL}/{orden.id}/reassignment", _reasignar(m.inactiva))

    assert response.status_code == 422
    assert response.json()["detail"]["field"] == "crew_id"


async def test_fecha_pasada_se_rechaza_con_el_campo(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m, OrderStatus.assigned)

    response = await _post(
        m.admin,
        f"{ORDERS_URL}/{orden.id}/reassignment",
        _reasignar(m.escuadrilla2, HOY - timedelta(days=1)),
    )

    assert response.status_code == 422
    assert response.json()["detail"]["field"] == "scheduled_for"


@pytest.mark.parametrize("status", [OrderStatus.pending, OrderStatus.done])
async def test_solo_se_reasigna_una_asignada_o_en_curso(mundo: Mundo, status: OrderStatus) -> None:
    m = mundo
    orden = await _orden(m, status)

    response = await _post(
        m.admin, f"{ORDERS_URL}/{orden.id}/reassignment", _reasignar(m.escuadrilla2)
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "invalid_transition"


async def test_orden_inexistente_da_404(mundo: Mundo) -> None:
    response = await _post(
        mundo.admin, f"{ORDERS_URL}/{uuid.uuid4()}/reassignment", _reasignar(mundo.escuadrilla2)
    )

    assert response.status_code == 404


@pytest.mark.parametrize("accion", ["reassignment", "unassignment"])
async def test_el_tecnico_no_puede(mundo: Mundo, accion: str) -> None:
    m = mundo
    orden = await _orden(m, OrderStatus.assigned)

    response = await _post(
        m.celular1, f"{ORDERS_URL}/{orden.id}/{accion}", _reasignar(m.escuadrilla2)
    )

    assert response.status_code == 403
    assert await _estado(orden.id) == OrderStatus.assigned
