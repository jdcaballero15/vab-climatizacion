"""E10: tablero con indicadores y los mismos filtros."""

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select, update

from app.core.dates import business_today
from app.db.models.catalog import Failure
from app.db.models.part import Part, PartUsage
from app.db.models.user import UserRole
from app.db.models.work_order import (
    WorkOrder,
    WorkOrderClosure,
    WorkOrderClosureTechnician,
    WorkOrderEvent,
)
from app.db.session import SessionLocal
from app.domain.work_order import ClosureOutcome, OrderStatus, WorkOrderEventType
from app.main import app
from tests import test_work_order_closure_admin as cierre
from tests.factories import make_user
from tests.test_work_order_closure_admin import Mundo, _auth, _orden, _seed

schema = cierre.schema
mundo = cierre.mundo
AHORA = datetime.now(UTC)


async def _get(user: Any, query: str = "") -> Response:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(f"/admin/dashboard{query}", headers=_auth(user))


async def _terminada(m: Mundo, *, dias: int = 1, falla: Failure | None = None) -> WorkOrder:
    """Orden creada y terminada hace unos días, con su cierre y un técnico tildado."""
    orden = await _orden(m, OrderStatus.done)
    cuando = AHORA - timedelta(days=dias)
    closure = WorkOrderClosure(
        work_order_id=orden.id,
        closed_by=m.celular.id,
        closed_at=cuando,
        idempotency_key=uuid.uuid4(),
        outcome=ClosureOutcome.done,
        failure_id=falla.id if falla else None,
    )
    await _seed(
        [
            closure,
            WorkOrderEvent(
                work_order_id=orden.id,
                event_type=WorkOrderEventType.status_change,
                from_status=OrderStatus.in_progress,
                to_status=OrderStatus.done,
                occurred_at=cuando,
            ),
        ]
    )
    return orden


# E10-01: por estado, igual que el panel (criterio 3), y la evolución por semana.
async def test_por_estado_y_evolucion(mundo: Mundo) -> None:
    m = mundo
    await _orden(m, OrderStatus.pending)
    await _terminada(m)

    body = (await _get(m.admin)).json()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        panel = await client.get("/admin/orders?status=pending", headers=_auth(m.admin))

    por_estado = {item["key"]: item["count"] for item in body["by_status"]}
    assert por_estado["pending"] == panel.json()["total"] == 1
    assert por_estado["done"] == 1
    assert sum(week["created"] for week in body["weeks"]) == 2
    assert sum(week["done"] for week in body["weeks"]) == 1
    assert body["totals"]["created"] == 2


# E10-02 y E10-03: técnicos por cierres, en curso por escuadrilla, fallas más comunes.
async def test_tecnicos_y_fallas(mundo: Mundo) -> None:
    m = mundo
    no_enfria = Failure(name="No enfría")
    await _seed([no_enfria])
    orden = await _terminada(m, falla=no_enfria)
    await _orden(m, OrderStatus.in_progress)
    async with SessionLocal() as session:
        closure = await session.scalar(
            select(WorkOrderClosure.id).where(WorkOrderClosure.work_order_id == orden.id)
        )
    tecnico = cierre.FieldTechnician(full_name="Ana Ficticia")
    await _seed([tecnico])
    await _seed([WorkOrderClosureTechnician(closure_id=closure, field_technician_id=tecnico.id)])

    body = (await _get(m.admin)).json()

    assert [(t["label"], t["count"]) for t in body["by_technician"]] == [("Ana Ficticia", 1)]
    assert [(c["label"], c["count"]) for c in body["in_progress_by_crew"]] == [("Escuadrilla 1", 1)]
    assert [(f["label"], f["count"]) for f in body["top_failures"]] == [("No enfría", 1)]


# E10-05: terminadas sin facturar, la más vieja primero, con días.
async def test_sin_facturar_la_mas_vieja_primero(mundo: Mundo) -> None:
    m = mundo
    nueva = await _terminada(m, dias=1)
    vieja = await _terminada(m, dias=10)

    body = (await _get(m.admin)).json()

    assert [(o["number"], o["days"]) for o in body["unbilled"]] == [
        (vieja.number, 10),
        (nueva.number, 1),
    ]


# E10-06: materiales más usados por cantidad.
async def test_materiales_mas_usados(mundo: Mundo) -> None:
    m = mundo
    orden = await _terminada(m)
    gas = Part(name="Gas R410A", unit="kg")
    await _seed([gas])
    async with SessionLocal() as session:
        closure_id = await session.scalar(
            select(WorkOrderClosure.id).where(WorkOrderClosure.work_order_id == orden.id)
        )
    await _seed(
        [
            PartUsage(
                work_order_id=orden.id,
                closure_id=closure_id,
                part_id=gas.id,
                quantity=Decimal("2.5"),
                created_by=m.celular.id,
            )
        ]
    )

    body = (await _get(m.admin)).json()

    assert [(p["label"], p["quantity"]) for p in body["top_parts"]] == [("Gas R410A (kg)", "2.500")]


# E10-08: los filtros recalculan todo y se comparan dos períodos.
async def test_filtros_y_comparacion(mundo: Mundo) -> None:
    m = mundo
    orden = await _terminada(m, dias=40)
    async with SessionLocal() as session:
        await session.execute(
            update(WorkOrderEvent)
            .where(
                WorkOrderEvent.work_order_id == orden.id,
                WorkOrderEvent.event_type == WorkOrderEventType.created,
            )
            .values(occurred_at=AHORA - timedelta(days=41))
        )
        await session.commit()
    hoy = business_today()
    mes_pasado = (hoy - timedelta(days=60), hoy - timedelta(days=31))

    otro_cliente = (await _get(m.admin, f"?client_id={uuid.uuid4()}")).json()
    comparado = (
        await _get(m.admin, f"?compare_from={mes_pasado[0]}&compare_to={mes_pasado[1]}")
    ).json()

    assert sum(item["count"] for item in otro_cliente["by_status"]) == 0
    assert otro_cliente["unbilled"] == []
    assert comparado["totals"]["done"] == 0
    assert comparado["compare"]["done"] == 1
    assert comparado["compare"]["created"] == 1


async def test_periodo_invalido(mundo: Mundo) -> None:
    response = await _get(mundo.admin, f"?date_from={date(2026, 2, 1)}&date_to={date(2026, 1, 1)}")
    assert response.status_code == 422


# E10-02, criterio 2: el técnico no ve el tablero; dirección sí.
@pytest.mark.parametrize(("role", "esperado"), [(UserRole.technician, 403), (UserRole.owner, 200)])
async def test_permisos(mundo: Mundo, role: UserRole, esperado: int) -> None:
    usuario = make_user(email=f"{role.value}@ot-demo.com", role=role)
    await _seed([usuario])
    assert (await _get(usuario)).status_code == esperado


# E11-03, criterio 3: el historial de Persat no se mezcla con las estadísticas.
async def test_el_historial_de_persat_no_cuenta(mundo: Mundo) -> None:
    m = mundo
    orden = await _terminada(m)
    async with SessionLocal() as session:
        await session.execute(
            update(WorkOrder).where(WorkOrder.id == orden.id).values(source="persat")
        )
        await session.commit()

    body = (await _get(m.admin)).json()

    assert sum(item["count"] for item in body["by_status"]) == 0
    assert body["unbilled"] == []
    assert body["totals"]["done"] == 0
