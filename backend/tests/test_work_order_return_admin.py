import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
from sqlalchemy import text, update

from app.db.models.crew import Crew
from app.db.models.work_order import (
    WorkOrder,
    WorkOrderBilling,
    WorkOrderClosure,
    WorkOrderEvent,
)
from app.db.session import SessionLocal, engine
from app.domain.work_order import (
    ClosureOutcome,
    OrderStatus,
    WorkOrderEventType,
)
from tests.test_work_order_reassignment_admin import (
    HOY,
    MANANA,
    ORDERS_URL,
    TABLES,
    Mundo,
    _asignaciones,
    _estado,
    _get,
    _ids_del_celular,
    _orden,
    _post,
    _seed,
    _ultimo_evento,
)
from tests.test_work_order_reassignment_admin import mundo as mundo

# E04-08, criterio 3: administración devuelve una orden Terminada a la escuadrilla que
# la cerró, con motivo. Vuelve Asignada y la escuadrilla ve el motivo en el celular.

MOTIVO = "Falta la foto del equipo."


# Las de la reasignación más la del cobro: una facturada no se devuelve.
TABLES_CON_COBRO = [*TABLES, WorkOrderBilling.__table__]
ENUMS = (
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
    "payment_method",
)


@pytest.fixture
async def schema() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(WorkOrder.metadata.create_all, tables=TABLES_CON_COBRO)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(WorkOrder.metadata.drop_all, tables=list(reversed(TABLES_CON_COBRO)))
        for enum_type in ENUMS:
            await conn.execute(text(f"DROP TYPE IF EXISTS {enum_type}"))
        await conn.execute(text("DROP SEQUENCE IF EXISTS work_order_number_seq"))


async def _terminada(m: Mundo) -> WorkOrder:
    """Orden cerrada como Resuelta por la Escuadrilla 1: la asignación sigue vigente."""
    orden = await _orden(m, OrderStatus.in_progress)
    async with SessionLocal() as session:
        await session.execute(
            update(WorkOrder).where(WorkOrder.id == orden.id).values(status=OrderStatus.done)
        )
        await session.commit()
    await _seed(
        [
            WorkOrderClosure(
                work_order_id=orden.id,
                closed_by=m.celular1.id,
                closed_at=datetime.now(UTC),
                idempotency_key=uuid.uuid4(),
                outcome=ClosureOutcome.done,
            )
        ]
    )
    return orden


def _devolver(reason: object = MOTIVO, day: object = MANANA) -> dict[str, object]:
    return {"reason": reason, "scheduled_for": str(day)}


def _url(orden: WorkOrder) -> str:
    return f"{ORDERS_URL}/{orden.id}/return"


# Criterio 3: vuelve Asignada a la misma escuadrilla, con el motivo en el evento.
async def test_devolver_una_terminada_la_deja_asignada_a_la_misma_escuadrilla(
    mundo: Mundo,
) -> None:
    m = mundo
    orden = await _terminada(m)

    response = await _post(m.admin, _url(orden), _devolver())

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["crew_id"] == str(m.escuadrilla1.id)
    assert body["scheduled_for"] == MANANA.isoformat()
    assert body["return_reason"] == MOTIVO
    assert await _estado(orden.id) == OrderStatus.assigned
    vieja, nueva = await _asignaciones(orden.id)
    assert vieja.unassigned_at is not None
    assert (nueva.crew_id, nueva.unassigned_at, nueva.return_reason) == (
        m.escuadrilla1.id,
        None,
        MOTIVO,
    )
    evento = await _ultimo_evento(orden.id)
    assert evento.event_type == WorkOrderEventType.review_returned
    assert (evento.from_status, evento.to_status) == (OrderStatus.done, OrderStatus.assigned)
    assert evento.actor_id == m.admin.id
    assert evento.note is not None and MOTIVO in evento.note


# Criterio 3: "con el motivo visible", para la escuadrilla en el celular.
async def test_la_escuadrilla_ve_el_motivo_en_la_lista_y_el_detalle(mundo: Mundo) -> None:
    m = mundo
    orden = await _terminada(m)
    await _post(m.admin, _url(orden), _devolver(day=HOY))

    [en_lista] = (await _get(m.celular1, "/tech/orders")).json()["orders"]
    assert (en_lista["id"], en_lista["return_reason"]) == (str(orden.id), MOTIVO)
    detalle = (await _get(m.celular1, f"/tech/orders/{orden.id}")).json()
    assert detalle["return_reason"] == MOTIVO


# Y para la oficina, en Asignadas.
async def test_asignadas_muestra_el_motivo_de_la_devolucion(mundo: Mundo) -> None:
    m = mundo
    orden = await _terminada(m)
    otra = await _orden(m, OrderStatus.assigned)
    await _post(m.admin, _url(orden), _devolver())

    items = (await _get(m.admin, f"{ORDERS_URL}?status=assigned")).json()["items"]
    motivos = {item["id"]: item["assignment"]["return_reason"] for item in items}
    assert motivos == {str(otra.id): None, str(orden.id): MOTIVO}


async def test_una_asignacion_comun_no_trae_motivo_de_devolucion(mundo: Mundo) -> None:
    m = mundo
    await _orden(m, OrderStatus.assigned)

    [en_lista] = (await _get(m.celular1, "/tech/orders")).json()["orders"]
    assert en_lista["return_reason"] is None


async def test_reasignar_una_devuelta_no_arrastra_el_motivo(mundo: Mundo) -> None:
    m = mundo
    orden = await _terminada(m)
    await _post(m.admin, _url(orden), _devolver())

    response = await _post(
        m.admin,
        f"{ORDERS_URL}/{orden.id}/reassignment",
        {"crew_id": str(m.escuadrilla2.id), "scheduled_for": MANANA.isoformat()},
    )

    assert response.status_code == 201
    assert (await _asignaciones(orden.id))[-1].return_reason is None


async def test_el_motivo_es_obligatorio(mundo: Mundo) -> None:
    m = mundo
    orden = await _terminada(m)

    for reason in ("", "   ", None):
        response = await _post(m.admin, _url(orden), _devolver(reason=reason))
        assert response.status_code == 422, reason
    assert await _estado(orden.id) == OrderStatus.done


async def test_la_fecha_no_puede_ser_anterior_a_hoy(mundo: Mundo) -> None:
    m = mundo
    orden = await _terminada(m)

    response = await _post(m.admin, _url(orden), _devolver(day="2020-01-01"))

    assert response.status_code == 422
    assert response.json()["detail"]["field"] == "scheduled_for"
    assert await _estado(orden.id) == OrderStatus.done


async def test_solo_se_devuelve_una_terminada(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m, OrderStatus.in_progress)

    response = await _post(m.admin, _url(orden), _devolver())

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "invalid_transition"


# Decisión de Gonza (2026-11-03): una aprobada ya tiene los precios estampados.
async def test_una_aprobada_no_se_devuelve(mundo: Mundo) -> None:
    m = mundo
    orden = await _terminada(m)
    await _seed(
        [
            WorkOrderEvent(
                work_order_id=orden.id,
                event_type=WorkOrderEventType.review_approved,
                actor_id=m.admin.id,
            )
        ]
    )

    response = await _post(m.admin, _url(orden), _devolver())

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "order_approved"
    assert await _estado(orden.id) == OrderStatus.done


# Una facturada ya no está Terminada: no se devuelve (E04-09).
async def test_una_facturada_no_se_devuelve(mundo: Mundo) -> None:
    m = mundo
    orden = await _terminada(m)
    async with SessionLocal() as session:
        await session.execute(
            update(WorkOrder).where(WorkOrder.id == orden.id).values(status=OrderStatus.invoiced)
        )
        await session.commit()

    response = await _post(m.admin, _url(orden), _devolver())

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "invalid_transition"
    assert await _estado(orden.id) == OrderStatus.invoiced


async def test_con_la_escuadrilla_desactivada_no_se_devuelve(mundo: Mundo) -> None:
    m = mundo
    orden = await _terminada(m)
    async with SessionLocal() as session:
        await session.execute(
            update(Crew).where(Crew.id == m.escuadrilla1.id).values(is_active=False)
        )
        await session.commit()

    response = await _post(m.admin, _url(orden), _devolver())

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "crew_not_available"
    assert await _estado(orden.id) == OrderStatus.done


async def test_orden_inexistente(mundo: Mundo) -> None:
    response = await _post(mundo.admin, f"{ORDERS_URL}/{uuid.uuid4()}/return", _devolver())

    assert response.status_code == 404


async def test_el_tecnico_no_puede_devolver(mundo: Mundo) -> None:
    m = mundo
    orden = await _terminada(m)

    response = await _post(m.celular1, _url(orden), _devolver())

    assert response.status_code == 403
    assert await _ids_del_celular(m.celular1) == []
