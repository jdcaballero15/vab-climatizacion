"""E07-03 y E07-04: planes de mantenimiento por equipo y generación de sus órdenes.

Decisión de Gonza (2026-11-03): un plan por equipo (cada cuántos meses, próxima visita,
escuadrilla que suele ir). Una semana antes de cada visita se genera la orden, Pendiente,
y la próxima visita se corre sola. Sin aprobación en bloque.
"""

import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import select, text, update

from app.db.models.catalog import EquipmentType, WorkType
from app.db.models.client import Client, ClientSite
from app.db.models.crew import Crew
from app.db.models.equipment import Equipment
from app.db.models.maintenance import MaintenanceCheckStep, MaintenancePlan
from app.db.models.user import User, UserRole
from app.db.models.work_order import WorkOrder, WorkOrderCheckItem, WorkOrderEvent
from app.db.session import SessionLocal, engine
from app.domain.work_order import OrderSource, OrderStatus, WorkOrderEventType
from app.services.maintenance import add_months
from tests.factories import make_user
from tests.test_work_order_reassignment_admin import HOY, _auth, _client, _get, _post, _seed
from tests.test_work_order_return_admin import ENUMS, TABLES_CON_COBRO

PLANS_URL = "/admin/maintenance/plans"
RUN_URL = "/admin/maintenance/run"
# La generación copia el checklist a cada orden (E07-01).
TABLES = [*TABLES_CON_COBRO, MaintenanceCheckStep.__table__, WorkOrderCheckItem.__table__]


@pytest.fixture
async def schema() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.create_all, tables=TABLES)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.drop_all, tables=list(reversed(TABLES)))
        for enum_type in ENUMS:
            await conn.execute(text(f"DROP TYPE IF EXISTS {enum_type}"))
        await conn.execute(text("DROP SEQUENCE IF EXISTS work_order_number_seq"))


@dataclass
class Mundo:
    admin: User
    celular: User
    escuadrilla: Crew
    inactiva: Crew
    cliente: Client
    sede: ClientSite
    split: Equipment
    rooftop: Equipment
    service: WorkType
    inactivo: WorkType


@pytest.fixture
async def mundo(schema: None) -> Mundo:
    admin = make_user(email="admin@ot-demo.com", role=UserRole.admin, full_name="Admin Ficticia")
    celular = make_user(email="esc1@ot-demo.com", role=UserRole.technician, full_name="Cel 1")
    await _seed([admin, celular])
    escuadrilla = Crew(name="Escuadrilla 1", app_user_id=celular.id)
    inactiva = Crew(name="Escuadrilla vieja", is_active=False)
    cliente = Client(id=uuid.uuid4(), number="10642", name="Hotel Ficticio")
    tipo = EquipmentType(name="Split")
    service = WorkType(name="Service")
    inactivo = WorkType(name="Mantenimiento viejo", is_active=False)
    await _seed([escuadrilla, inactiva, cliente, tipo, service, inactivo])
    sede = ClientSite(client_id=cliente.id, label="Central", address="Calle 1")
    await _seed([sede])
    split = Equipment(
        client_site_id=sede.id,
        equipment_type_id=tipo.id,
        internal_code="EA1064201",
        location_note="Habitación 12",
    )
    rooftop = Equipment(
        client_site_id=sede.id,
        equipment_type_id=tipo.id,
        internal_code="EA1064202",
        location_note="Terraza",
    )
    await _seed([split, rooftop])
    return Mundo(
        admin=admin,
        celular=celular,
        escuadrilla=escuadrilla,
        inactiva=inactiva,
        cliente=cliente,
        sede=sede,
        split=split,
        rooftop=rooftop,
        service=service,
        inactivo=inactivo,
    )


def _plan(m: Mundo, **cambios: Any) -> dict[str, Any]:
    base = {
        "equipment_id": str(m.split.id),
        "work_type_id": str(m.service.id),
        "crew_id": str(m.escuadrilla.id),
        "every_months": 3,
        "next_due_on": (HOY + timedelta(days=3)).isoformat(),
    }
    return base | cambios


async def _patch(user: User, url: str, payload: dict[str, Any]) -> Any:
    async with _client() as client:
        return await client.patch(url, json=payload, headers=_auth(user))


async def _crear(m: Mundo, **cambios: Any) -> dict[str, Any]:
    response = await _post(m.admin, PLANS_URL, _plan(m, **cambios))
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def _correr(m: Mundo) -> dict[str, Any]:
    response = await _post(m.admin, RUN_URL, {})
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


async def _ordenes() -> list[WorkOrder]:
    async with SessionLocal() as session:
        return list(await session.scalars(select(WorkOrder).order_by(WorkOrder.number)))


async def _plan_guardado(plan_id: str) -> MaintenancePlan:
    async with SessionLocal() as session:
        plan = await session.get(MaintenancePlan, uuid.UUID(plan_id))
        assert plan is not None
        return plan


async def _mover_visita(plan_id: str, dia: date) -> None:
    async with SessionLocal() as session:
        await session.execute(
            update(MaintenancePlan)
            .where(MaintenancePlan.id == uuid.UUID(plan_id))
            .values(next_due_on=dia)
        )
        await session.commit()


# ---- E07-03: planes ----


# Criterio 1: el plan queda con su equipo, cliente, frecuencia y próxima visita.
async def test_crear_un_plan(mundo: Mundo) -> None:
    m = mundo

    body = await _crear(m, notes="  Llevar escalera  ")

    assert body["equipment"] == {
        "id": str(m.split.id),
        "internal_code": "EA1064201",
        "location_note": "Habitación 12",
        "equipment_type_name": "Split",
    }
    assert body["client"]["name"] == "Hotel Ficticio"
    assert body["work_type"] == {"id": str(m.service.id), "name": "Service"}
    assert body["crew"] == {"id": str(m.escuadrilla.id), "name": "Escuadrilla 1"}
    assert (body["every_months"], body["notes"]) == (3, "Llevar escalera")
    assert (body["active"], body["ends_on"], body["open_order"]) == (True, None, None)


# Criterio 3: un equipo no puede estar en dos planes activos.
async def test_un_equipo_no_entra_en_dos_planes_activos(mundo: Mundo) -> None:
    m = mundo
    await _crear(m)

    response = await _post(m.admin, PLANS_URL, _plan(m, every_months=6))

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "equipment_already_in_plan"


async def test_con_el_plan_terminado_el_equipo_entra_en_otro(mundo: Mundo) -> None:
    # Terminar hoy ("Terminar" en la pantalla): desde hoy ya no está activo.
    m = mundo
    viejo = await _crear(m)
    response = await _patch(m.admin, f"{PLANS_URL}/{viejo['id']}", {"ends_on": HOY.isoformat()})
    assert response.status_code == 200, response.text
    assert response.json()["active"] is False

    nuevo = await _crear(m, every_months=6)

    assert nuevo["active"] is True
    # Criterio 2: el terminado queda como historial.
    response = await _get(m.admin, f"{PLANS_URL}?include_ended=true")
    assert {plan["id"] for plan in response.json()} == {viejo["id"], nuevo["id"]}
    response = await _get(m.admin, PLANS_URL)
    assert [plan["id"] for plan in response.json()] == [nuevo["id"]]

    # Reabrir el viejo dejaría al equipo en dos planes.
    response = await _patch(m.admin, f"{PLANS_URL}/{viejo['id']}", {"ends_on": None})
    assert response.status_code == 409


async def test_editar_un_plan(mundo: Mundo) -> None:
    m = mundo
    plan = await _crear(m)

    response = await _patch(
        m.admin,
        f"{PLANS_URL}/{plan['id']}",
        {"every_months": 6, "crew_id": None, "next_due_on": "2027-01-15"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["every_months"], body["crew"], body["next_due_on"]) == (6, None, "2027-01-15")


@pytest.mark.parametrize(
    ("cambio", "codigo"),
    [
        ("tipo_inactivo", "work_type_not_available"),
        ("escuadrilla_inactiva", "crew_not_available"),
        ("equipo_dado_de_baja", "equipment_not_available"),
        ("frecuencia_cero", None),
    ],
)
async def test_rechaza_datos_que_no_sirven(mundo: Mundo, cambio: str, codigo: str | None) -> None:
    m = mundo
    if cambio == "equipo_dado_de_baja":
        async with SessionLocal() as session:
            await session.execute(
                update(Equipment)
                .where(Equipment.id == m.split.id)
                .values(deleted_at=datetime.now(UTC))
            )
            await session.commit()
    payload = {
        "tipo_inactivo": _plan(m, work_type_id=str(m.inactivo.id)),
        "escuadrilla_inactiva": _plan(m, crew_id=str(m.inactiva.id)),
        "equipo_dado_de_baja": _plan(m),
        "frecuencia_cero": _plan(m, every_months=0),
    }[cambio]

    response = await _post(m.admin, PLANS_URL, payload)

    assert response.status_code == 422
    if codigo is not None:
        assert response.json()["detail"]["code"] == codigo


async def test_el_tecnico_no_ve_ni_toca_los_planes(mundo: Mundo) -> None:
    m = mundo

    assert (await _get(m.celular, PLANS_URL)).status_code == 403
    assert (await _post(m.celular, PLANS_URL, _plan(m))).status_code == 403
    assert (await _post(m.celular, RUN_URL, {})).status_code == 403


# ---- E07-04: generación ----


# Criterios 1 y 3: la visita de la semana genera su orden Pendiente, con el equipo.
async def test_genera_la_orden_de_la_visita_de_la_semana(mundo: Mundo) -> None:
    m = mundo
    visita = HOY + timedelta(days=3)
    plan = await _crear(m, next_due_on=visita.isoformat(), notes="Llevar escalera")

    resumen = await _correr(m)

    [orden] = await _ordenes()
    assert resumen["generated"] == [
        {
            "order_id": str(orden.id),
            "number": orden.number,
            "client_name": "Hotel Ficticio",
            "equipment_code": "EA1064201",
            "due_on": visita.isoformat(),
        }
    ]
    assert resumen["skipped"] == []
    assert (orden.status, orden.source) == (OrderStatus.pending, OrderSource.maintenance)
    assert (orden.equipment_id, orden.client_site_id) == (m.split.id, m.sede.id)
    assert (orden.work_type_id, orden.description) == (m.service.id, "Llevar escalera")
    assert orden.requires_approval is False
    async with SessionLocal() as session:
        [evento] = await session.scalars(
            select(WorkOrderEvent).where(WorkOrderEvent.work_order_id == orden.id)
        )
    assert evento.event_type == WorkOrderEventType.created
    assert evento.note == "Generada por el plan de mantenimiento (cada 3 meses)."
    # La próxima visita se corre los meses del plan.
    assert (await _plan_guardado(plan["id"])).next_due_on == add_months(visita, 3)

    # La oficina la ve en Pendientes, con la escuadrilla del plan para asignar.
    response = await _get(m.admin, "/admin/orders?status=pending")
    [item] = response.json()["items"]
    assert item["maintenance"] == {
        "due_on": visita.isoformat(),
        "every_months": 3,
        "crew_id": str(m.escuadrilla.id),
    }
    # Y el plan muestra su orden abierta.
    response = await _get(m.admin, PLANS_URL)
    assert response.json()[0]["open_order"] == {
        "id": str(orden.id),
        "number": orden.number,
        "status": "pending",
        "due_on": visita.isoformat(),
    }


# Criterio 2: correr dos veces no duplica, ni aunque la visita vuelva a quedar pendiente.
async def test_correr_dos_veces_no_duplica(mundo: Mundo) -> None:
    m = mundo
    visita = HOY + timedelta(days=1)
    plan = await _crear(m, next_due_on=visita.isoformat())
    await _correr(m)

    assert (await _correr(m))["generated"] == []
    await _mover_visita(plan["id"], visita)
    resumen = await _correr(m)

    assert resumen["generated"] == []
    assert len(await _ordenes()) == 1
    assert (await _plan_guardado(plan["id"])).next_due_on == add_months(visita, 3)


async def test_no_genera_lo_que_falta_mas_de_una_semana(mundo: Mundo) -> None:
    m = mundo
    await _crear(m, next_due_on=(HOY + timedelta(days=8)).isoformat())

    assert (await _correr(m))["generated"] == []
    assert await _ordenes() == []


# E07-03, criterio 2: con fin, no se generan visitas posteriores.
async def test_no_genera_visitas_despues_del_fin_del_abono(mundo: Mundo) -> None:
    m = mundo
    await _crear(
        m,
        next_due_on=(HOY + timedelta(days=3)).isoformat(),
        ends_on=(HOY + timedelta(days=2)).isoformat(),
    )

    assert (await _correr(m))["generated"] == []


# Criterios 4 y 5: lo que no se puede generar queda en el resumen con el motivo.
async def test_omite_el_equipo_dado_de_baja_y_lo_informa(mundo: Mundo) -> None:
    m = mundo
    plan = await _crear(m)
    async with SessionLocal() as session:
        await session.execute(
            update(Equipment).where(Equipment.id == m.split.id).values(deleted_at=datetime.now(UTC))
        )
        await session.commit()

    resumen = await _correr(m)

    assert resumen["generated"] == []
    assert resumen["skipped"] == [
        {"plan_id": plan["id"], "equipment_code": "EA1064201", "reason": "equipment_deleted"}
    ]
    assert await _ordenes() == []


# Un plan atrasado genera una sola orden y la próxima visita queda en el futuro.
async def test_un_plan_atrasado_genera_una_sola_orden(mundo: Mundo) -> None:
    m = mundo
    atrasada = HOY - timedelta(days=100)
    plan = await _crear(m, every_months=1, next_due_on=atrasada.isoformat())

    resumen = await _correr(m)

    assert [item["due_on"] for item in resumen["generated"]] == [atrasada.isoformat()]
    proxima = (await _plan_guardado(plan["id"])).next_due_on
    assert HOY <= proxima <= add_months(HOY, 1)


async def test_genera_un_plan_por_equipo(mundo: Mundo) -> None:
    m = mundo
    await _crear(m)
    await _crear(m, equipment_id=str(m.rooftop.id), crew_id=None)

    resumen = await _correr(m)

    assert sorted(item["equipment_code"] for item in resumen["generated"]) == [
        "EA1064201",
        "EA1064202",
    ]


@pytest.mark.parametrize(
    ("dia", "meses", "esperado"),
    [
        (date(2026, 1, 31), 1, date(2026, 2, 28)),
        (date(2026, 11, 15), 3, date(2027, 2, 15)),
        (date(2027, 8, 31), 6, date(2028, 2, 29)),
    ],
)
def test_sumar_meses(dia: date, meses: int, esperado: date) -> None:
    assert add_months(dia, meses) == esperado
