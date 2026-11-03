"""E04-06: el detalle de la orden con su línea de tiempo, para la oficina y dirección."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import update

from app.db.models.user import UserRole
from app.db.models.work_order import WorkOrder, WorkOrderBilling, WorkOrderEvent
from app.db.session import SessionLocal
from app.domain.work_order import (
    BillingStatus,
    OrderChannel,
    OrderStatus,
    WorkOrderEventType,
)
from tests.factories import make_user
from tests.test_work_order_closure_admin import (
    AYER,
    ORDERS_URL,
    Mundo,
    _cierre,
    _get,
    _orden,
    _seed,
)
from tests.test_work_order_closure_admin import mundo as mundo
from tests.test_work_order_closure_admin import schema as schema

INICIO = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)


async def _terminada_con_historia(m: Mundo) -> WorkOrder:
    """Creada, asignada, iniciada, cerrada, aprobada y facturada, con quién y cuándo."""
    orden = await _orden(m, OrderStatus.done)
    async with SessionLocal() as session:
        await session.execute(
            update(WorkOrder)
            .where(WorkOrder.id == orden.id)
            .values(
                description="Pierde agua",
                channel=OrderChannel.whatsapp,
                requester_name="Marta Ficticia",
                requester_area="Planta baja",
            )
        )
        await session.execute(
            update(WorkOrderEvent)
            .where(WorkOrderEvent.work_order_id == orden.id)
            .values(occurred_at=INICIO, actor_id=m.admin.id)
        )
        await session.commit()

    def evento(horas: int, tipo: WorkOrderEventType, **values: object) -> WorkOrderEvent:
        return WorkOrderEvent(
            work_order_id=orden.id,
            event_type=tipo,
            occurred_at=INICIO + timedelta(hours=horas),
            **values,
        )

    await _seed(
        [
            evento(
                1,
                WorkOrderEventType.assigned,
                from_status=OrderStatus.pending,
                to_status=OrderStatus.assigned,
                actor_id=m.admin.id,
                note="Escuadrilla: Escuadrilla 1. Fecha prevista: 21/10/2026.",
            ),
            evento(
                20,
                WorkOrderEventType.status_change,
                from_status=OrderStatus.assigned,
                to_status=OrderStatus.in_progress,
                actor_id=m.celular.id,
            ),
            evento(
                22,
                WorkOrderEventType.status_change,
                from_status=OrderStatus.in_progress,
                to_status=OrderStatus.done,
                actor_id=m.celular.id,
                note="Resuelta.",
            ),
            evento(30, WorkOrderEventType.review_approved, actor_id=m.admin.id, note="Aprobada."),
        ]
    )
    await _cierre(m, orden, closed_at=INICIO + timedelta(hours=22))
    await _seed(
        [
            WorkOrderBilling(
                work_order_id=orden.id,
                parts_amount=Decimal("0"),
                labor_amount=Decimal("1000"),
                status=BillingStatus.invoiced,
                invoice_number="A-0001-00000001",
                updated_by=m.admin.id,
            )
        ]
    )
    return orden


# Criterio 1: los datos de la orden en una sola respuesta.
async def test_detalle_con_los_datos_de_la_orden(mundo: Mundo) -> None:
    m = mundo
    orden = await _terminada_con_historia(m)

    response = await _get(m.admin, f"{ORDERS_URL}/{orden.id}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["number"] == orden.number
    assert body["status"] == "done"
    assert body["kind"] == "on_site"
    assert datetime.fromisoformat(body["created_at"]) == INICIO
    assert body["client"] == {
        "id": str(m.sede.client_id),
        "number": "10642",
        "name": "Sanatorio Ficticio",
    }
    assert body["site"] == {"label": "Central", "address": "Calle 1", "reference": None}
    assert body["work_type_name"] == "Reparación"
    assert body["equipment"] is None
    assert (body["description"], body["channel"]) == ("Pierde agua", "whatsapp")
    assert (body["requester_name"], body["requester_area"]) == ("Marta Ficticia", "Planta baja")
    assert body["assignment"] == {
        "crew_name": "Escuadrilla 1",
        "scheduled_for": AYER.date().isoformat(),
        "return_reason": None,
    }
    assert body["has_closure"] is True
    assert body["cancellation"] is None


# Criterio 2: cada paso con quién y cuándo, del más viejo al más nuevo.
async def test_linea_de_tiempo_con_usuario_y_fecha(mundo: Mundo) -> None:
    m = mundo
    orden = await _terminada_con_historia(m)

    body = (await _get(m.admin, f"{ORDERS_URL}/{orden.id}")).json()

    pasos = [
        (e["event_type"], e["to_status"], e["actor_name"], e["note"]) for e in body["timeline"]
    ]
    assert pasos == [
        ("created", "pending", "Admin Ficticia", None),
        (
            "assigned",
            "assigned",
            "Admin Ficticia",
            "Escuadrilla: Escuadrilla 1. Fecha prevista: 21/10/2026.",
        ),
        ("status_change", "in_progress", "Celular 1", None),
        ("status_change", "done", "Celular 1", "Resuelta."),
        ("review_approved", None, "Admin Ficticia", "Aprobada."),
        # El cobro de E04-14 no deja evento: se arma con su registro.
        ("billing_invoiced", None, "Admin Ficticia", "Factura A-0001-00000001"),
    ]
    fechas = [datetime.fromisoformat(e["occurred_at"]) for e in body["timeline"]]
    assert fechas[:5] == [INICIO + timedelta(hours=h) for h in (0, 1, 20, 22, 30)]


async def test_sin_facturar_no_hay_paso_de_factura(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m, OrderStatus.assigned)

    body = (await _get(m.admin, f"{ORDERS_URL}/{orden.id}")).json()

    assert [e["event_type"] for e in body["timeline"]] == ["created"]
    assert body["has_closure"] is False
    # Un evento sin usuario (los migrados o los del sistema) no tiene nombre.
    assert body["timeline"][0]["actor_name"] is None


async def test_orden_inexistente(mundo: Mundo) -> None:
    response = await _get(mundo.admin, f"{ORDERS_URL}/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "order_not_found"


async def test_el_tecnico_no_ve_el_detalle_de_administracion(mundo: Mundo) -> None:
    orden = await _orden(mundo, OrderStatus.assigned)

    response = await _get(mundo.celular, f"{ORDERS_URL}/{orden.id}")

    assert response.status_code == 403


async def test_direccion_ve_el_detalle(mundo: Mundo) -> None:
    direccion = make_user(email="direccion@ot-demo.com", role=UserRole.owner)
    await _seed([direccion])
    orden = await _orden(mundo, OrderStatus.assigned)

    response = await _get(direccion, f"{ORDERS_URL}/{orden.id}")

    assert response.status_code == 200
