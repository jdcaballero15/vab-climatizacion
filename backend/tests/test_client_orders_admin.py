import uuid
from datetime import UTC, datetime, timedelta

from app.db.models.catalog import EquipmentType, WorkType
from app.db.models.client import Client, ClientSite
from app.db.models.equipment import Equipment
from app.db.models.user import UserRole
from app.db.models.work_order import (
    WorkOrder,
    WorkOrderAssignment,
    WorkOrderClosure,
    WorkOrderEvent,
)
from app.domain.work_order import ClosureOutcome, NotDoneReason, OrderStatus, WorkOrderEventType
from tests.factories import make_user, make_work_order
from tests.test_work_order_reassignment_admin import HOY, Mundo, _get, _seed
from tests.test_work_order_reassignment_admin import mundo as mundo
from tests.test_work_order_reassignment_admin import schema as schema

# E03-04: el historial de órdenes en la ficha del cliente.

BASE = datetime(2026, 10, 20, 15, 0, tzinfo=UTC)


def _url(client_id: uuid.UUID, query: str = "") -> str:
    return f"/admin/clients/{client_id}/orders{query}"


async def _orden(
    m: Mundo,
    status: OrderStatus,
    creada: datetime,
    *,
    sede: ClientSite | None = None,
    tipo: WorkType | None = None,
    equipo: Equipment | None = None,
) -> WorkOrder:
    item = make_work_order(
        client_site=sede or m.sede, work_type=tipo or m.reparacion, status=status
    )
    item.equipment_id = equipo.id if equipo else None
    await _seed([item])
    await _seed(
        [
            WorkOrderEvent(
                work_order_id=item.id,
                event_type=WorkOrderEventType.created,
                to_status=OrderStatus.pending,
                occurred_at=creada,
            )
        ]
    )
    return item


async def _asignar(m: Mundo, orden: WorkOrder, cuando: datetime, *, vigente: bool = True) -> None:
    await _seed(
        [
            WorkOrderAssignment(
                work_order_id=orden.id,
                crew_id=m.escuadrilla1.id,
                scheduled_for=HOY,
                assigned_at=cuando,
                unassigned_at=None if vigente else cuando + timedelta(hours=2),
            )
        ]
    )


async def _cerrar(m: Mundo, orden: WorkOrder, cuando: datetime, outcome: ClosureOutcome) -> None:
    await _seed(
        [
            WorkOrderClosure(
                work_order_id=orden.id,
                closed_by=m.celular1.id,
                closed_at=cuando,
                idempotency_key=uuid.uuid4(),
                outcome=outcome,
                not_done_reason=(
                    NotDoneReason.client_absent if outcome == ClosureOutcome.not_done else None
                ),
            )
        ]
    )


# Criterio 1: sus órdenes, la más nueva primero, con escuadrilla (asignada o la que cerró).
async def test_historial_con_lo_necesario_de_cada_orden(mundo: Mundo) -> None:
    m = mundo
    tipo_equipo = EquipmentType(name="Aire acondicionado")
    await _seed([tipo_equipo])
    equipo = Equipment(
        client_site_id=m.sede.id,
        equipment_type_id=tipo_equipo.id,
        internal_code="EA900",
        location_note="Sala de máquinas",
    )
    await _seed([equipo])

    pendiente = await _orden(m, OrderStatus.pending, BASE)
    terminada = await _orden(m, OrderStatus.done, BASE + timedelta(days=1), equipo=equipo)
    await _asignar(m, terminada, BASE + timedelta(days=1, hours=1))
    await _cerrar(m, terminada, BASE + timedelta(days=1, hours=5), ClosureOutcome.done)
    # Volvió a Pendientes desde la escuadrilla: la asignación terminó, el cierre queda.
    volvio = await _orden(m, OrderStatus.pending, BASE + timedelta(days=2))
    await _asignar(m, volvio, BASE + timedelta(days=2, hours=1), vigente=False)
    await _cerrar(m, volvio, BASE + timedelta(days=2, hours=2), ClosureOutcome.not_done)
    asignada = await _orden(m, OrderStatus.assigned, BASE + timedelta(days=3))
    await _asignar(m, asignada, BASE + timedelta(days=3, hours=1))
    # De otro cliente: no aparece.
    otro = Client(id=uuid.uuid4(), number="20001", name="Hotel Ficticio")
    await _seed([otro])
    sede_otro = ClientSite(client_id=otro.id, label="Única", address="Calle 2")
    await _seed([sede_otro])
    await _orden(m, OrderStatus.pending, BASE, sede=sede_otro)

    response = await _get(m.admin, _url(m.sede.client_id))

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["total"], body["limit"], body["offset"]) == (4, 20, 0)
    items = body["items"]
    assert [item["id"] for item in items] == [
        str(asignada.id),
        str(volvio.id),
        str(terminada.id),
        str(pendiente.id),
    ]
    resumen = [(i["status"], i["crew_name"], i["has_closure"]) for i in items]
    assert resumen == [
        ("assigned", "Escuadrilla 1", False),
        ("pending", "Escuadrilla 1", True),
        ("done", "Escuadrilla 1", True),
        ("pending", None, False),
    ]
    con_equipo = items[2]
    assert con_equipo["number"] == terminada.number
    assert con_equipo["work_type_name"] == "Reparación"
    assert (con_equipo["site_label"], con_equipo["site_address"]) == ("Central", "Calle 1")
    assert con_equipo["equipment"] == {
        "id": str(equipo.id),
        "internal_code": "EA900",
        "location_note": "Sala de máquinas",
    }
    assert datetime.fromisoformat(con_equipo["created_at"]) == BASE + timedelta(days=1)
    assert items[0]["equipment"] is None


# Criterio 3: 20 por página.
async def test_historial_paginado_de_a_20(mundo: Mundo) -> None:
    m = mundo
    for n in range(23):
        await _orden(m, OrderStatus.pending, BASE + timedelta(hours=n))

    primera = (await _get(m.admin, _url(m.sede.client_id))).json()
    segunda = (await _get(m.admin, _url(m.sede.client_id, "?offset=20"))).json()

    assert (primera["total"], len(primera["items"])) == (23, 20)
    assert (segunda["total"], len(segunda["items"])) == (23, 3)
    ids = {i["id"] for i in primera["items"]} | {i["id"] for i in segunda["items"]}
    assert len(ids) == 23


# Criterio 3: filtra por equipo, tipo de trabajo y período de creación.
async def test_historial_filtra_por_equipo_tipo_y_periodo(mundo: Mundo) -> None:
    m = mundo
    tipo_equipo = EquipmentType(name="Heladera comercial")
    service = WorkType(name="Service")
    await _seed([tipo_equipo, service])
    equipo = Equipment(
        client_site_id=m.sede.id,
        equipment_type_id=tipo_equipo.id,
        internal_code="HC100",
        location_note="Cocina",
    )
    await _seed([equipo])
    con_equipo = await _orden(m, OrderStatus.pending, BASE, equipo=equipo)
    de_service = await _orden(m, OrderStatus.pending, BASE, tipo=service)
    # 10/10 a las 02:00 UTC es todavía el 9/10 en Argentina.
    del_9 = await _orden(m, OrderStatus.pending, datetime(2026, 10, 10, 2, 0, tzinfo=UTC))
    del_10 = await _orden(m, OrderStatus.pending, datetime(2026, 10, 10, 4, 0, tzinfo=UTC))
    client_id = m.sede.client_id

    async def ids(query: str) -> list[str]:
        response = await _get(m.admin, _url(client_id, query))
        assert response.status_code == 200, response.text
        return sorted(item["id"] for item in response.json()["items"])

    assert await ids(f"?equipment_id={equipo.id}") == [str(con_equipo.id)]
    assert await ids(f"?work_type_id={service.id}") == [str(de_service.id)]
    assert await ids("?created_from=2026-10-10&created_to=2026-10-10") == [str(del_10.id)]
    assert await ids("?created_to=2026-10-09") == [str(del_9.id)]
    assert await ids("?created_from=2026-10-11") == sorted([str(con_equipo.id), str(de_service.id)])


# Criterio 5: sin órdenes, la lista viene vacía (el mensaje lo pone la app).
async def test_cliente_sin_ordenes(mundo: Mundo) -> None:
    body = (await _get(mundo.admin, _url(mundo.sede.client_id))).json()

    assert (body["items"], body["total"]) == ([], 0)


async def test_cliente_inexistente(mundo: Mundo) -> None:
    response = await _get(mundo.admin, _url(uuid.uuid4()))

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "client_not_found"


# Criterio 4: el técnico no ve el historial. Dirección sí.
async def test_el_tecnico_no_ve_el_historial(mundo: Mundo) -> None:
    response = await _get(mundo.celular1, _url(mundo.sede.client_id))

    assert response.status_code == 403


async def test_direccion_ve_el_historial(mundo: Mundo) -> None:
    m = mundo
    direccion = make_user(email="direccion@ot-demo.com", role=UserRole.owner)
    await _seed([direccion])
    await _orden(m, OrderStatus.pending, BASE)

    response = await _get(direccion, _url(m.sede.client_id))

    assert response.status_code == 200
    assert response.json()["total"] == 1
