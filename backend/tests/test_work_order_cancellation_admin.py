import uuid
from collections.abc import AsyncGenerator, Sequence
from dataclasses import dataclass
from datetime import datetime
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
from app.domain.work_order import CancelReason, OrderStatus, WorkOrderEventType
from app.main import app
from tests.factories import make_user, make_work_order

# E04-07: administración cancela una orden con motivo.

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


async def _orden(m: Mundo, status: OrderStatus = OrderStatus.pending) -> WorkOrder:
    """Orden con su evento de creación y, si está Asignada o En curso, su asignación."""
    item = make_work_order(client_site=m.sede, work_type=m.reparacion, status=status)
    item.description = "Cámara no enfría"
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
                    work_order_id=item.id, crew_id=m.escuadrilla.id, scheduled_for=HOY
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


async def _cancelar(user: User, order_id: object, payload: dict[str, Any]) -> Response:
    async with _client() as client:
        return await client.post(
            f"{ORDERS_URL}/{order_id}/cancellation", json=payload, headers=_auth(user)
        )


async def _get(user: User, url: str) -> Response:
    async with _client() as client:
        return await client.get(url, headers=_auth(user))


def _detail(response: Response) -> dict[str, Any]:
    detail: dict[str, Any] = response.json()["detail"]
    return detail


async def _leer(order_id: uuid.UUID) -> tuple[OrderStatus, list[WorkOrderEvent]]:
    async with SessionLocal() as session:
        status = await session.scalar(select(WorkOrder.status).where(WorkOrder.id == order_id))
        eventos = await session.scalars(
            select(WorkOrderEvent)
            .where(WorkOrderEvent.work_order_id == order_id)
            .order_by(WorkOrderEvent.occurred_at)
        )
        assert status is not None
        return status, list(eventos)


async def _cancelaciones() -> list[WorkOrderCancellation]:
    async with SessionLocal() as session:
        return list(await session.scalars(select(WorkOrderCancellation)))


async def _sin_cambios(orden: WorkOrder, status: OrderStatus) -> None:
    estado, eventos = await _leer(orden.id)
    assert estado == status
    assert [e.event_type for e in eventos] == [WorkOrderEventType.created]
    assert await _cancelaciones() == []


# ---- Cancelar (criterios 1 y 2) ----


# Criterio 1: desde Pendiente, Asignada o En curso pasa a Cancelada con el motivo en el evento.
@pytest.mark.parametrize(
    "status", [OrderStatus.pending, OrderStatus.assigned, OrderStatus.in_progress]
)
async def test_cancelar_pasa_a_cancelada_con_el_motivo(mundo: Mundo, status: OrderStatus) -> None:
    m = mundo
    orden = await _orden(m, status)

    response = await _cancelar(m.admin, orden.id, {"reason": "duplicate"})

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["reason"] == "duplicate"
    assert body["reason_text"] is None
    assert body["cancelled_by_name"] == "Admin Ficticia"
    assert body["cancelled_at"]
    estado, eventos = await _leer(orden.id)
    assert estado == OrderStatus.cancelled
    evento = eventos[-1]
    assert evento.event_type == WorkOrderEventType.status_change
    assert evento.from_status == status
    assert evento.to_status == OrderStatus.cancelled
    assert evento.actor_id == m.admin.id
    assert evento.note == "Duplicada."
    (cancelacion,) = await _cancelaciones()
    assert cancelacion.work_order_id == orden.id
    assert cancelacion.reason == CancelReason.duplicate
    assert cancelacion.cancelled_by == m.admin.id


@pytest.mark.parametrize(
    ("reason", "nota"),
    [
        ("entered_by_mistake", "Cargada por error."),
        ("duplicate", "Duplicada."),
        ("client_cancelled", "El cliente la canceló."),
    ],
)
async def test_cada_motivo_de_la_lista(mundo: Mundo, reason: str, nota: str) -> None:
    orden = await _orden(mundo)

    response = await _cancelar(mundo.admin, orden.id, {"reason": reason})

    assert response.status_code == 201, response.text
    _, eventos = await _leer(orden.id)
    assert eventos[-1].note == nota


# Criterio 2: "Otro" con texto.
async def test_otro_con_texto(mundo: Mundo) -> None:
    orden = await _orden(mundo)

    response = await _cancelar(
        mundo.admin, orden.id, {"reason": "other", "reason_text": "  Se mudó   de sede "}
    )

    assert response.status_code == 201, response.text
    assert response.json()["reason_text"] == "Se mudó de sede"
    _, eventos = await _leer(orden.id)
    assert eventos[-1].note == "Otro: Se mudó de sede"


# Criterio 2: sin motivo, o "Otro" sin texto, se rechaza con el campo.
@pytest.mark.parametrize(
    ("payload", "campo"),
    [
        ({}, "reason"),
        ({"reason": None}, "reason"),
        ({"reason": "no_existe"}, "reason"),
        ({"reason": "other"}, "reason_text"),
        ({"reason": "other", "reason_text": "   "}, "reason_text"),
        ({"reason": "duplicate", "reason_text": "Ya estaba"}, "reason_text"),
    ],
    ids=[
        "sin-motivo",
        "motivo-nulo",
        "motivo-inexistente",
        "otro-sin-texto",
        "otro-en-blanco",
        "texto-sin-otro",
    ],
)
async def test_motivo_incompleto_se_rechaza_con_el_campo(
    mundo: Mundo, payload: dict[str, Any], campo: str
) -> None:
    orden = await _orden(mundo)

    response = await _cancelar(mundo.admin, orden.id, payload)

    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    campos = (
        {detail["field"]}
        if isinstance(detail, dict)
        else {str(error["loc"][-1]) for error in detail}
    )
    assert campo in campos
    await _sin_cambios(orden, OrderStatus.pending)


async def test_campo_de_mas_se_rechaza(mundo: Mundo) -> None:
    orden = await _orden(mundo)

    response = await _cancelar(
        mundo.admin, orden.id, {"reason": "duplicate", "status": "cancelled"}
    )

    assert response.status_code == 422


# ---- La escuadrilla deja de verla (criterio 4) ----


@pytest.mark.parametrize("status", [OrderStatus.assigned, OrderStatus.in_progress])
async def test_termina_la_asignacion_y_la_escuadrilla_deja_de_verla(
    mundo: Mundo, status: OrderStatus
) -> None:
    m = mundo
    orden = await _orden(m, status)
    otra = await _orden(m, OrderStatus.assigned)

    response = await _cancelar(m.admin, orden.id, {"reason": "client_cancelled"})

    assert response.status_code == 201, response.text
    async with SessionLocal() as session:
        asignacion = await session.scalar(
            select(WorkOrderAssignment).where(WorkOrderAssignment.work_order_id == orden.id)
        )
        assert asignacion is not None
        assert asignacion.unassigned_at is not None
    lista = await _get(m.celular, "/tech/orders")
    assert [o["id"] for o in lista.json()["orders"]] == [str(otra.id)]
    detalle = await _get(m.celular, f"/tech/orders/{orden.id}")
    assert detalle.status_code == 404
    assert _detail(detalle)["code"] == "order_not_found"


async def test_el_cierre_de_una_orden_cancelada_da_404(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m, OrderStatus.in_progress)
    await _cancelar(m.admin, orden.id, {"reason": "entered_by_mistake"})

    async with _client() as client:
        opciones = await client.get(
            f"/tech/orders/{orden.id}/closure-options", headers=_auth(m.celular)
        )
        cierre = await client.post(
            f"/tech/orders/{orden.id}/closure",
            json={
                "idempotency_key": str(uuid.uuid4()),
                "outcome": "done",
                "technician_ids": [str(uuid.uuid4())],
                "task_ids": [],
                "equipment_condition": "working",
            },
            headers=_auth(m.celular),
        )

    assert opciones.status_code == 404
    assert cierre.status_code == 404
    assert _detail(cierre)["code"] == "order_not_found"


# ---- No se puede (criterio 5) ----


@pytest.mark.parametrize(
    "status",
    [OrderStatus.done, OrderStatus.invoiced, OrderStatus.paid, OrderStatus.cancelled],
)
async def test_desde_terminada_en_adelante_se_rechaza(mundo: Mundo, status: OrderStatus) -> None:
    orden = await _orden(mundo, status)

    response = await _cancelar(mundo.admin, orden.id, {"reason": "duplicate"})

    assert response.status_code == 409, response.text
    assert _detail(response)["code"] == "invalid_transition"
    await _sin_cambios(orden, status)


async def test_cancelar_dos_veces_se_rechaza(mundo: Mundo) -> None:
    orden = await _orden(mundo)
    await _cancelar(mundo.admin, orden.id, {"reason": "duplicate"})

    response = await _cancelar(mundo.admin, orden.id, {"reason": "duplicate"})

    assert response.status_code == 409
    assert len(await _cancelaciones()) == 1


async def test_orden_inexistente(mundo: Mundo) -> None:
    response = await _cancelar(mundo.admin, uuid.uuid4(), {"reason": "duplicate"})

    assert response.status_code == 404
    assert _detail(response)["code"] == "order_not_found"


@pytest.mark.parametrize("role", [UserRole.technician, UserRole.owner])
async def test_otros_roles_reciben_403(mundo: Mundo, role: UserRole) -> None:
    orden = await _orden(mundo)
    user = make_user(email=f"otro-{role.value}@ot-demo.com", role=role)
    await _seed([user])

    response = await _cancelar(user, orden.id, {"reason": "duplicate"})

    assert response.status_code == 403
    await _sin_cambios(orden, OrderStatus.pending)


# ---- Listado por estado (criterio 6; Asignadas y En curso para cancelar desde ahí) ----


async def test_canceladas_con_motivo_quien_y_cuando(mundo: Mundo) -> None:
    m = mundo
    primera = await _orden(m)
    segunda = await _orden(m, OrderStatus.assigned)
    await _orden(m)
    await _cancelar(m.admin, primera.id, {"reason": "duplicate"})
    await _cancelar(m.admin, segunda.id, {"reason": "other", "reason_text": "Se mudó"})

    response = await _get(m.admin, f"{ORDERS_URL}?status=cancelled")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 2
    # La última cancelada primero.
    assert [item["id"] for item in body["items"]] == [str(segunda.id), str(primera.id)]
    item = body["items"][0]
    assert item["status"] == "cancelled"
    assert item["assignment"] is None
    assert item["returned"] is None
    assert item["cancellation"]["reason"] == "other"
    assert item["cancellation"]["reason_text"] == "Se mudó"
    assert item["cancellation"]["cancelled_by_name"] == "Admin Ficticia"
    assert item["cancellation"]["cancelled_at"]


@pytest.mark.parametrize("status", [OrderStatus.assigned, OrderStatus.in_progress])
async def test_abiertas_con_escuadrilla_y_fecha(mundo: Mundo, status: OrderStatus) -> None:
    m = mundo
    orden = await _orden(m, status)
    await _orden(m)

    response = await _get(m.admin, f"{ORDERS_URL}?status={status.value}")

    assert response.status_code == 200, response.text
    (item,) = response.json()["items"]
    assert item["id"] == str(orden.id)
    assert item["status"] == status.value
    assert item["client_name"] == "Sanatorio Ficticio"
    assert item["assignment"] == {"crew_name": "Escuadrilla 1", "scheduled_for": HOY.isoformat()}
    assert item["cancellation"] is None


async def test_pendientes_sin_asignacion_ni_cancelacion(mundo: Mundo) -> None:
    orden = await _orden(mundo)

    response = await _get(mundo.admin, f"{ORDERS_URL}?status=pending")

    (item,) = response.json()["items"]
    assert item["id"] == str(orden.id)
    assert item["status"] == "pending"
    assert item["assignment"] is None
    assert item["cancellation"] is None


# Las terminadas se listan desde E04-08; facturadas y cobradas llegan con E04-05.
@pytest.mark.parametrize("status", ["invoiced", "paid"])
async def test_el_listado_todavia_no_admite_facturadas_ni_cobradas(
    mundo: Mundo, status: str
) -> None:
    response = await _get(mundo.admin, f"{ORDERS_URL}?status={status}")

    assert response.status_code == 422
