"""E06: órdenes de taller con etapas en fila (retiro, galpón, devolución), opción A.

Entre una etapa y la siguiente la orden vuelve a Pendiente para que la oficina la asigne;
al cerrar la devolución queda Terminada (decisión de Gonza, 2026-11-03).
"""

import uuid
from typing import Any

from sqlalchemy import select, update

from app.db.models.user import User, UserRole
from app.db.models.work_order import (
    WorkOrder,
    WorkOrderAssignment,
    WorkOrderClosure,
    WorkOrderEvent,
)
from app.db.session import SessionLocal
from app.domain.work_order import (
    OrderKind,
    OrderStatus,
    SignaturePurpose,
    WorkOrderEventType,
    WorkshopStage,
)
from tests.factories import make_user
from tests.test_tech_order_closure import (
    Mundo,
    _auth,
    _cerrar,
    _client,
    _detail,
    _firma,
    _firmada,
    _firmas,
    _leer,
    _opciones,
    _orden,
    _resuelta,
    _seed,
)
from tests.test_tech_order_closure import mundo as mundo
from tests.test_tech_order_closure import schema as schema


async def _de_taller(m: Mundo, etapa: WorkshopStage) -> WorkOrder:
    """Una orden de taller En curso en esa etapa, asignada a la Escuadrilla 1."""
    orden = await _orden(m)
    async with SessionLocal() as session:
        await session.execute(
            update(WorkOrder)
            .where(WorkOrder.id == orden.id)
            .values(kind=OrderKind.workshop, workshop_stage=etapa)
        )
        await session.commit()
    # Los listados de la oficina parten del evento de creación.
    await _seed(
        [
            WorkOrderEvent(
                work_order_id=orden.id,
                event_type=WorkOrderEventType.created,
                to_status=OrderStatus.pending,
            )
        ]
    )
    return orden


async def _orden_guardada(order_id: uuid.UUID) -> WorkOrder:
    async with SessionLocal() as session:
        orden = await session.get(WorkOrder, order_id)
        assert orden is not None
        return orden


async def _asignacion_vigente(order_id: uuid.UUID) -> WorkOrderAssignment | None:
    async with SessionLocal() as session:
        return await session.scalar(
            select(WorkOrderAssignment).where(
                WorkOrderAssignment.work_order_id == order_id,
                WorkOrderAssignment.unassigned_at.is_(None),
            )
        )


async def _ultimo_cierre(order_id: uuid.UUID) -> WorkOrderClosure:
    async with SessionLocal() as session:
        cierre = await session.scalar(
            select(WorkOrderClosure)
            .where(WorkOrderClosure.work_order_id == order_id)
            .order_by(WorkOrderClosure.closed_at.desc())
            .limit(1)
        )
        assert cierre is not None
        return cierre


def _entrega(m: Mundo, file_id: uuid.UUID, **cambios: Any) -> dict[str, Any]:
    """Retiro o devolución hecha: firma y nombre, sin falla, reparación ni estado del equipo."""
    base = {
        "failure_id": None,
        "repair_id": None,
        "task_ids": [],
        "equipment_condition": None,
    }
    return _firmada(m, file_id, **(base | cambios))


def _galpon(m: Mundo, **cambios: Any) -> dict[str, Any]:
    """Trabajo en el galpón: como un cierre resuelto, sin firma ni motivo."""
    return _resuelta(m, **({"no_signature_reason": None} | cambios))


# ---- E06-02: "Requiere retiro" convierte la orden en el lugar ----


async def test_requiere_retiro_pasa_la_orden_a_taller(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m)

    response = await _cerrar(
        m.celular,
        orden.id,
        _resuelta(m, outcome="needs_pickup", failure_id=None, repair_id=None),
    )

    assert response.status_code == 201, response.text
    assert response.json()["order_status"] == "pending"
    guardada = await _orden_guardada(orden.id)
    assert (guardada.kind, guardada.workshop_stage) == (OrderKind.workshop, WorkshopStage.pickup)
    assert guardada.number == orden.number
    assert await _asignacion_vigente(orden.id) is None
    status, eventos, cierres = await _leer(orden.id)
    assert (status, cierres) == (OrderStatus.pending, 1)
    tipos = [e.event_type for e in eventos]
    assert tipos[-2:] == [
        WorkOrderEventType.status_change,
        WorkOrderEventType.converted_to_workshop,
    ]
    # El cierre de la visita no es de una etapa de taller.
    assert (await _ultimo_cierre(orden.id)).workshop_stage is None


async def test_una_de_taller_no_vuelve_a_pedir_retiro(mundo: Mundo) -> None:
    m = mundo
    orden = await _de_taller(m, WorkshopStage.workshop)

    response = await _cerrar(m.celular, orden.id, _galpon(m, outcome="needs_pickup"))

    assert response.status_code == 422
    assert _detail(response)["code"] == "already_workshop"


# ---- E06-04: retiro con firma ----


async def test_retiro_firmado_deja_el_equipo_en_el_galpon(mundo: Mundo) -> None:
    m = mundo
    orden = await _de_taller(m, WorkshopStage.pickup)
    firma = await _firma(m.celular)

    response = await _cerrar(m.celular, orden.id, _entrega(m, firma.id))

    assert response.status_code == 201, response.text
    assert response.json()["order_status"] == "pending"
    guardada = await _orden_guardada(orden.id)
    assert (guardada.status, guardada.workshop_stage) == (
        OrderStatus.pending,
        WorkshopStage.workshop,
    )
    assert await _asignacion_vigente(orden.id) is None
    assert (await _ultimo_cierre(orden.id)).workshop_stage == WorkshopStage.pickup
    [firmada] = await _firmas(orden.id)
    assert firmada.purpose == SignaturePurpose.pickup
    _, eventos, _ = await _leer(orden.id)
    assert eventos[-1].note == "Retiro hecho: el equipo está en el galpón."


async def test_retiro_sin_firma_se_rechaza(mundo: Mundo) -> None:
    m = mundo
    orden = await _de_taller(m, WorkshopStage.pickup)
    sin_firma = _resuelta(m, failure_id=None, repair_id=None, task_ids=[], equipment_condition=None)

    response = await _cerrar(m.celular, orden.id, sin_firma)

    assert response.status_code == 422
    assert _detail(response)["field"] == "signature"


async def test_retiro_que_no_se_pudo_hacer_sigue_en_retiro(mundo: Mundo) -> None:
    m = mundo
    orden = await _de_taller(m, WorkshopStage.pickup)
    payload = _resuelta(
        m,
        outcome="not_done",
        not_done_reason="client_absent",
        failure_id=None,
        repair_id=None,
        equipment_condition=None,
    )

    response = await _cerrar(m.celular, orden.id, payload)

    assert response.status_code == 201, response.text
    guardada = await _orden_guardada(orden.id)
    assert (guardada.status, guardada.workshop_stage) == (
        OrderStatus.pending,
        WorkshopStage.pickup,
    )


# ---- E06-05: trabajo en el galpón ----


async def test_galpon_termina_y_queda_para_la_devolucion(mundo: Mundo) -> None:
    m = mundo
    orden = await _de_taller(m, WorkshopStage.workshop)

    response = await _cerrar(m.celular, orden.id, _galpon(m))

    assert response.status_code == 201, response.text
    guardada = await _orden_guardada(orden.id)
    assert (guardada.status, guardada.workshop_stage) == (
        OrderStatus.pending,
        WorkshopStage.delivery,
    )
    assert await _firmas(orden.id) == []


async def test_galpon_pide_falla_y_reparacion(mundo: Mundo) -> None:
    m = mundo
    orden = await _de_taller(m, WorkshopStage.workshop)

    response = await _cerrar(m.celular, orden.id, _galpon(m, failure_id=None, repair_id=None))

    assert response.status_code == 422
    assert _detail(response)["field"] == "failure_id"


async def test_galpon_no_se_firma(mundo: Mundo) -> None:
    m = mundo
    orden = await _de_taller(m, WorkshopStage.workshop)
    firma = await _firma(m.celular)

    response = await _cerrar(m.celular, orden.id, _firmada(m, firma.id))

    assert response.status_code == 422
    assert _detail(response)["code"] == "signature_not_allowed"


# ---- E06-06 y E06-08: devolución firmada, la orden queda Terminada ----


async def test_devolucion_firmada_termina_la_orden(mundo: Mundo) -> None:
    m = mundo
    orden = await _de_taller(m, WorkshopStage.delivery)
    firma = await _firma(m.celular)

    response = await _cerrar(m.celular, orden.id, _entrega(m, firma.id))

    assert response.status_code == 201, response.text
    assert response.json()["order_status"] == "done"
    guardada = await _orden_guardada(orden.id)
    assert (guardada.status, guardada.workshop_stage) == (
        OrderStatus.done,
        WorkshopStage.delivery,
    )
    [firmada] = await _firmas(orden.id)
    assert firmada.purpose == SignaturePurpose.delivery
    _, eventos, _ = await _leer(orden.id)
    assert eventos[-1].note == "Devolución hecha: el cliente recibió el equipo."


# ---- Lo que ve la escuadrilla ----


async def test_la_escuadrilla_ve_la_etapa(mundo: Mundo) -> None:
    m = mundo
    orden = await _de_taller(m, WorkshopStage.pickup)

    opciones = (await _opciones(m.celular, orden.id)).json()

    assert opciones["workshop_stage"] == "pickup"


async def test_en_el_lugar_no_hay_etapa(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m)

    opciones = (await _opciones(m.celular, orden.id)).json()

    assert opciones["workshop_stage"] is None


# ---- E06-01: la oficina crea una orden de taller ----


async def _admin() -> User:
    admin = make_user(email="admin@ot-demo.com", role=UserRole.admin, full_name="Admin Ficticia")
    await _seed([admin])
    return admin


async def test_la_oficina_crea_una_orden_de_taller_que_arranca_en_el_retiro(
    mundo: Mundo,
) -> None:
    m = mundo
    admin = await _admin()
    pedido = {
        "client_id": str(m.sede.client_id),
        "client_site_id": str(m.sede.id),
        "work_type_id": str(m.reparacion.id),
        "channel": "phone",
        "description": "Retirar la heladera para cambiarle el compresor",
        "kind": "workshop",
    }

    async with _client() as client:
        response = await client.post("/admin/orders", json=pedido, headers=_auth(admin))

    assert response.status_code == 201, response.text
    body = response.json()
    assert (body["kind"], body["workshop_stage"], body["status"]) == (
        "workshop",
        "pickup",
        "pending",
    )


async def test_sin_decir_el_tipo_es_en_el_lugar(mundo: Mundo) -> None:
    m = mundo
    admin = await _admin()
    pedido = {
        "client_id": str(m.sede.client_id),
        "client_site_id": str(m.sede.id),
        "work_type_id": str(m.reparacion.id),
        "channel": "phone",
        "description": "No enfría",
    }

    async with _client() as client:
        response = await client.post("/admin/orders", json=pedido, headers=_auth(admin))

    assert (response.json()["kind"], response.json()["workshop_stage"]) == ("on_site", None)


# ---- E06-07: qué equipos están en el galpón y en qué etapa ----


async def test_en_el_galpon_estan_los_retirados_sin_devolver(mundo: Mundo) -> None:
    m = mundo
    admin = await _admin()
    en_retiro = await _de_taller(m, WorkshopStage.pickup)
    en_galpon = await _de_taller(m, WorkshopStage.workshop)
    por_devolver = await _de_taller(m, WorkshopStage.delivery)
    devuelta = await _de_taller(m, WorkshopStage.delivery)
    en_el_lugar = await _orden(m)
    async with SessionLocal() as session:
        await session.execute(
            update(WorkOrder).where(WorkOrder.id == devuelta.id).values(status=OrderStatus.done)
        )
        await session.commit()

    async with _client() as client:
        response = await client.get("/admin/orders/in-workshop", headers=_auth(admin))

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert [(i["id"], i["workshop_stage"]) for i in items] == [
        (str(en_galpon.id), "workshop"),
        (str(por_devolver.id), "delivery"),
    ]
    ids = {i["id"] for i in items}
    assert not ids & {str(en_retiro.id), str(devuelta.id), str(en_el_lugar.id)}
    assert items[0]["assignment"]["crew_name"] == "Escuadrilla 1"


async def test_el_tecnico_no_ve_el_galpon(mundo: Mundo) -> None:
    async with _client() as client:
        response = await client.get("/admin/orders/in-workshop", headers=_auth(mundo.celular))

    assert response.status_code == 403
