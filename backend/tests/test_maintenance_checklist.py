"""E07-01, E07-06 y E07-08: checklist único de mantenimiento, OK / No OK y reparación.

Decisión de Gonza (2026-11-03): una sola lista de pasos, editable por la oficina. Cada
orden generada se lleva una copia; la escuadrilla marca cada paso OK o No OK, con
observación obligatoria en No OK, y puede marcar "requiere reparación".
"""

import uuid
from collections.abc import AsyncGenerator, Sequence
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select, text, update

from app.core.security import create_access_token
from app.db.models.catalog import EquipmentType, Failure, Repair, Task, WorkType
from app.db.models.client import Client, ClientContact, ClientSite
from app.db.models.crew import Crew, FieldTechnician
from app.db.models.equipment import Equipment
from app.db.models.maintenance import MaintenanceCheckStep, MaintenancePlan
from app.db.models.part import Part, PartPrice, PartUsage
from app.db.models.signature import Signature
from app.db.models.stored_file import StoredFile
from app.db.models.user import User, UserRole
from app.db.models.work_order import (
    WorkOrder,
    WorkOrderAssignment,
    WorkOrderCancellation,
    WorkOrderCheckItem,
    WorkOrderClosure,
    WorkOrderClosureCheck,
    WorkOrderClosurePhoto,
    WorkOrderClosureTask,
    WorkOrderClosureTechnician,
    WorkOrderEvent,
)
from app.db.session import SessionLocal, engine
from app.domain.work_order import OrderStatus
from app.main import app
from tests.factories import make_user, make_work_order
from tests.test_tech_order_closure import HOY

STEPS_URL = "/admin/maintenance/check-steps"
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
    MaintenancePlan.__table__,
    MaintenanceCheckStep.__table__,
    WorkOrder.__table__,
    WorkOrderEvent.__table__,
    WorkOrderAssignment.__table__,
    WorkOrderCheckItem.__table__,
    WorkOrderClosure.__table__,
    WorkOrderClosureTechnician.__table__,
    WorkOrderClosureTask.__table__,
    WorkOrderClosureCheck.__table__,
    WorkOrderCancellation.__table__,
    StoredFile.__table__,
    WorkOrderClosurePhoto.__table__,
    Signature.__table__,
    Part.__table__,
    PartPrice.__table__,
    PartUsage.__table__,
]


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
            "workshop_stage",
            "cancel_reason",
            "closure_outcome",
            "equipment_condition",
            "not_done_reason",
            "no_signature_reason",
            "signature_purpose",
            "check_result",
        ):
            await conn.execute(text(f"DROP TYPE IF EXISTS {enum_type}"))
        await conn.execute(text("DROP SEQUENCE IF EXISTS work_order_number_seq"))


@dataclass
class Mundo:
    admin: User
    celular: User
    escuadrilla: Crew
    ana: FieldTechnician
    sede: ClientSite
    equipo: Equipment
    service: WorkType
    no_enfria: Failure
    carga_de_gas: Repair
    filtros: MaintenanceCheckStep
    drenaje: MaintenanceCheckStep
    prueba: MaintenanceCheckStep


@pytest.fixture
async def mundo(schema: None) -> Mundo:
    admin = make_user(email="admin@ot-demo.com", role=UserRole.admin, full_name="Admin Ficticia")
    celular = make_user(email="esc1@ot-demo.com", role=UserRole.technician, full_name="Cel 1")
    await _seed([admin, celular])
    escuadrilla = Crew(name="Escuadrilla 1", app_user_id=celular.id)
    ana = FieldTechnician(full_name="Ana Ficticia")
    cliente = Client(id=uuid.uuid4(), number="10642", name="Hotel Ficticio")
    tipo = EquipmentType(name="Split")
    # Service pide falla y reparación; con checklist, solo si un paso lo requiere (E07-08).
    service = WorkType(name="Service", requires_failure_repair=True)
    no_enfria = Failure(name="No enfría")
    filtros = MaintenanceCheckStep(name="Limpieza de filtros", position=0)
    drenaje = MaintenanceCheckStep(name="Revisión del drenaje", position=1)
    prueba = MaintenanceCheckStep(name="Prueba de funcionamiento", position=2)
    await _seed([escuadrilla, ana, cliente, tipo, service, no_enfria, filtros, drenaje, prueba])
    sede = ClientSite(client_id=cliente.id, label="Central", address="Calle 1")
    carga_de_gas = Repair(name="Carga de gas", failure_id=no_enfria.id)
    await _seed([sede, carga_de_gas])
    equipo = Equipment(
        client_site_id=sede.id,
        equipment_type_id=tipo.id,
        internal_code="EA1064201",
        location_note="Habitación 12",
    )
    await _seed([equipo])
    return Mundo(
        admin=admin,
        celular=celular,
        escuadrilla=escuadrilla,
        ana=ana,
        sede=sede,
        equipo=equipo,
        service=service,
        no_enfria=no_enfria,
        carga_de_gas=carga_de_gas,
        filtros=filtros,
        drenaje=drenaje,
        prueba=prueba,
    )


async def _seed(items: Sequence[object]) -> None:
    async with SessionLocal() as session:
        session.add_all(list(items))
        await session.commit()


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


async def _call(method: str, user: User, url: str, payload: object = None) -> Response:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.request(method, url, json=payload, headers=_auth(user))


async def _generar(m: Mundo) -> WorkOrder:
    """Plan con visita en tres días: "Generar ahora" crea su orden con el checklist."""
    plan = MaintenancePlan(
        equipment_id=m.equipo.id,
        work_type_id=m.service.id,
        crew_id=m.escuadrilla.id,
        every_months=3,
        next_due_on=HOY + timedelta(days=3),
    )
    await _seed([plan])
    response = await _call("POST", m.admin, "/admin/maintenance/run")
    assert response.status_code == 200, response.text
    [generada] = response.json()["generated"]
    async with SessionLocal() as session:
        order = await session.get(WorkOrder, uuid.UUID(generada["order_id"]))
        assert order is not None
        return order


async def _en_curso(m: Mundo, order: WorkOrder) -> None:
    """La pone En curso en la escuadrilla, sin pasar por la asignación y el inicio."""
    async with SessionLocal() as session:
        await session.execute(
            update(WorkOrder).where(WorkOrder.id == order.id).values(status=OrderStatus.in_progress)
        )
        session.add(
            WorkOrderAssignment(work_order_id=order.id, crew_id=m.escuadrilla.id, scheduled_for=HOY)
        )
        await session.commit()


async def _items(order_id: uuid.UUID) -> list[WorkOrderCheckItem]:
    async with SessionLocal() as session:
        stmt = (
            select(WorkOrderCheckItem)
            .where(WorkOrderCheckItem.work_order_id == order_id)
            .order_by(WorkOrderCheckItem.position)
        )
        return list(await session.scalars(stmt))


def _ok(item: WorkOrderCheckItem) -> dict[str, Any]:
    return {"check_item_id": str(item.id), "result": "ok"}


def _no_ok(item: WorkOrderCheckItem, *, reparar: bool = False) -> dict[str, Any]:
    return {
        "check_item_id": str(item.id),
        "result": "not_ok",
        "observation": "Bandeja tapada",
        "requires_repair": reparar,
    }


def _cierre(m: Mundo, checklist: list[dict[str, Any]], **cambios: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "idempotency_key": str(uuid.uuid4()),
        "outcome": "done",
        "technician_ids": [str(m.ana.id)],
        "equipment_condition": "working",
        "no_signature_reason": "client_absent",
        "checklist": checklist,
    }
    return payload | cambios


async def _cerrar(m: Mundo, order: WorkOrder, payload: dict[str, Any]) -> Response:
    return await _call("POST", m.celular, f"/tech/orders/{order.id}/closure", payload)


def _error(response: Response) -> tuple[int, str]:
    return response.status_code, response.json()["detail"]["code"]


# ---- E07-01: la oficina edita el checklist ----


async def test_alta_de_un_paso_va_al_final_y_entra_en_la_orden_generada(mundo: Mundo) -> None:
    m = mundo
    response = await _call("POST", m.admin, STEPS_URL, {"name": "  Control   de presiones "})
    assert response.status_code == 201, response.text
    assert response.json()["name"] == "Control de presiones"

    lista = (await _call("GET", m.admin, STEPS_URL)).json()
    assert [paso["name"] for paso in lista] == [
        "Limpieza de filtros",
        "Revisión del drenaje",
        "Prueba de funcionamiento",
        "Control de presiones",
    ]
    order = await _generar(m)
    assert [item.name for item in await _items(order.id)] == [paso["name"] for paso in lista]


async def test_nombre_repetido_se_rechaza(mundo: Mundo) -> None:
    response = await _call("POST", mundo.admin, STEPS_URL, {"name": "limpieza DE filtros"})
    assert _error(response) == (409, "check_step_name_already_exists")


async def test_reordenar_los_pasos(mundo: Mundo) -> None:
    m = mundo
    nuevo = [str(m.prueba.id), str(m.filtros.id), str(m.drenaje.id)]

    response = await _call("PUT", m.admin, f"{STEPS_URL}/order", {"step_ids": nuevo})

    assert response.status_code == 200, response.text
    assert [paso["id"] for paso in response.json()] == nuevo
    # Sin todos los activos (otra pestaña sumó o quitó uno), se rechaza.
    incompleto = {"step_ids": nuevo[:2]}
    response = await _call("PUT", m.admin, f"{STEPS_URL}/order", incompleto)
    assert _error(response) == (422, "check_step_order_mismatch")


# Criterio 3: las órdenes ya generadas conservan los pasos con que se generaron.
async def test_editar_el_checklist_no_cambia_las_ordenes_generadas(mundo: Mundo) -> None:
    m = mundo
    order = await _generar(m)

    url = f"{STEPS_URL}/{m.filtros.id}"
    response = await _call("PATCH", m.admin, url, {"name": "Lavado de filtros"})
    assert response.status_code == 200, response.text

    assert [item.name for item in await _items(order.id)] == [
        "Limpieza de filtros",
        "Revisión del drenaje",
        "Prueba de funcionamiento",
    ]


# Criterio 4: quitar un paso lo desactiva; no se copia a las órdenes nuevas.
async def test_desactivar_un_paso(mundo: Mundo) -> None:
    m = mundo
    url = f"{STEPS_URL}/{m.drenaje.id}"
    response = await _call("PATCH", m.admin, url, {"is_active": False})
    assert response.status_code == 200, response.text

    activos = (await _call("GET", m.admin, STEPS_URL)).json()
    assert [paso["name"] for paso in activos] == ["Limpieza de filtros", "Prueba de funcionamiento"]
    todos = (await _call("GET", m.admin, f"{STEPS_URL}?include_inactive=true")).json()
    assert len(todos) == 3
    order = await _generar(m)
    assert [item.name for item in await _items(order.id)] == [
        "Limpieza de filtros",
        "Prueba de funcionamiento",
    ]
    # Reactivado vuelve al final.
    await _call("PATCH", m.admin, url, {"is_active": True})
    activos = (await _call("GET", m.admin, STEPS_URL)).json()
    assert activos[-1]["name"] == "Revisión del drenaje"


# Criterio 5: el técnico no ve ni edita el checklist de la oficina.
async def test_el_tecnico_no_gestiona_el_checklist(mundo: Mundo) -> None:
    m = mundo
    url = f"{STEPS_URL}/{m.filtros.id}"
    assert (await _call("GET", m.celular, STEPS_URL)).status_code == 403
    assert (await _call("POST", m.celular, STEPS_URL, {"name": "Otro"})).status_code == 403
    assert (await _call("PATCH", m.celular, url, {"is_active": False})).status_code == 403
    response = await _call("PUT", m.celular, f"{STEPS_URL}/order", {"step_ids": []})
    assert response.status_code == 403


# ---- E07-06: la escuadrilla completa el checklist ----


async def test_opciones_traen_el_checklist_sin_pedir_falla(mundo: Mundo) -> None:
    m = mundo
    order = await _generar(m)
    await _en_curso(m, order)

    response = await _call("GET", m.celular, f"/tech/orders/{order.id}/closure-options")

    assert response.status_code == 200, response.text
    body = response.json()
    items = await _items(order.id)
    assert body["checklist"] == [{"id": str(item.id), "name": item.name} for item in items]
    assert body["requires_failure_repair"] is False


async def test_cerrar_con_ok_y_no_ok(mundo: Mundo) -> None:
    m = mundo
    order = await _generar(m)
    await _en_curso(m, order)
    filtros, drenaje, prueba = await _items(order.id)

    response = await _cerrar(m, order, _cierre(m, [_ok(filtros), _no_ok(drenaje), _ok(prueba)]))

    assert response.status_code == 201, response.text
    async with SessionLocal() as session:
        checks = list(await session.scalars(select(WorkOrderClosureCheck)))
    assert {(c.check_item_id, c.result, c.observation) for c in checks} == {
        (filtros.id, "ok", None),
        (drenaje.id, "not_ok", "Bandeja tapada"),
        (prueba.id, "ok", None),
    }


async def test_faltan_pasos_sin_responder(mundo: Mundo) -> None:
    m = mundo
    order = await _generar(m)
    await _en_curso(m, order)
    filtros, _drenaje, prueba = await _items(order.id)

    response = await _cerrar(m, order, _cierre(m, [_ok(filtros), _ok(prueba)]))

    assert _error(response) == (422, "checklist_incomplete")
    assert response.json()["detail"]["field"] == "checklist"


async def test_no_ok_pide_observacion(mundo: Mundo) -> None:
    m = mundo
    order = await _generar(m)
    await _en_curso(m, order)
    filtros, drenaje, prueba = await _items(order.id)
    sin_texto = _no_ok(drenaje) | {"observation": "   "}

    response = await _cerrar(m, order, _cierre(m, [_ok(filtros), sin_texto, _ok(prueba)]))

    assert _error(response) == (422, "checklist_observation_required")


async def test_ok_no_lleva_reparacion(mundo: Mundo) -> None:
    m = mundo
    order = await _generar(m)
    await _en_curso(m, order)
    filtros, drenaje, prueba = await _items(order.id)
    ok_raro = _ok(filtros) | {"requires_repair": True}

    response = await _cerrar(m, order, _cierre(m, [ok_raro, _ok(drenaje), _ok(prueba)]))

    assert _error(response) == (422, "checklist_ok_with_details")


async def test_no_se_pudo_hacer_va_sin_checklist(mundo: Mundo) -> None:
    m = mundo
    order = await _generar(m)
    await _en_curso(m, order)
    filtros, drenaje, prueba = await _items(order.id)
    no_hecha = {"outcome": "not_done", "not_done_reason": "client_absent"}

    response = await _cerrar(
        m, order, _cierre(m, [_ok(filtros), _ok(drenaje), _ok(prueba)], **no_hecha)
    )
    assert _error(response) == (422, "checklist_not_allowed")

    sin_checklist = _cierre(m, [], equipment_condition=None, **no_hecha)
    response = await _cerrar(m, order, sin_checklist)
    assert response.status_code == 201, response.text


async def test_una_orden_comun_no_lleva_checklist(mundo: Mundo) -> None:
    m = mundo
    comun = make_work_order(client_site=m.sede, work_type=m.service)
    await _seed([comun])
    await _en_curso(m, comun)
    async with SessionLocal() as session:
        comun = await session.get(WorkOrder, comun.id)  # type: ignore[assignment]
    respuesta_ajena = {"check_item_id": str(uuid.uuid4()), "result": "ok"}

    response = await _cerrar(m, comun, _cierre(m, [respuesta_ajena]))

    assert _error(response) == (422, "checklist_not_allowed")


async def test_paso_de_otra_orden_se_rechaza(mundo: Mundo) -> None:
    m = mundo
    order = await _generar(m)
    await _en_curso(m, order)
    filtros, drenaje, _prueba = await _items(order.id)
    ajeno = {"check_item_id": str(uuid.uuid4()), "result": "ok"}

    response = await _cerrar(m, order, _cierre(m, [_ok(filtros), _ok(drenaje), ajeno]))

    assert _error(response) == (422, "checklist_item_not_available")


# ---- E07-08: "requiere reparación" ----


async def test_requiere_reparacion_pide_falla_y_reparacion(mundo: Mundo) -> None:
    m = mundo
    order = await _generar(m)
    await _en_curso(m, order)
    filtros, drenaje, prueba = await _items(order.id)
    checklist = [_ok(filtros), _no_ok(drenaje, reparar=True), _ok(prueba)]

    response = await _cerrar(m, order, _cierre(m, checklist))
    assert _error(response) == (422, "failure_required")

    con_reparacion = _cierre(
        m, checklist, failure_id=str(m.no_enfria.id), repair_id=str(m.carga_de_gas.id)
    )
    response = await _cerrar(m, order, con_reparacion)
    assert response.status_code == 201, response.text


# Criterios 2 y 3: la orden conserva las dos partes y la oficina las ve juntas.
async def test_la_oficina_ve_checklist_y_reparacion(mundo: Mundo) -> None:
    m = mundo
    order = await _generar(m)
    await _en_curso(m, order)
    filtros, drenaje, prueba = await _items(order.id)
    payload = _cierre(
        m,
        [_ok(filtros), _no_ok(drenaje, reparar=True), _ok(prueba)],
        failure_id=str(m.no_enfria.id),
        repair_id=str(m.carga_de_gas.id),
    )
    assert (await _cerrar(m, order, payload)).status_code == 201

    response = await _call("GET", m.admin, f"/admin/orders/{order.id}/closure")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["failure"] == "No enfría"
    assert body["repair"] == "Carga de gas"
    assert body["checklist"] == [
        {
            "name": "Limpieza de filtros",
            "result": "ok",
            "observation": None,
            "requires_repair": False,
        },
        {
            "name": "Revisión del drenaje",
            "result": "not_ok",
            "observation": "Bandeja tapada",
            "requires_repair": True,
        },
        {
            "name": "Prueba de funcionamiento",
            "result": "ok",
            "observation": None,
            "requires_repair": False,
        },
    ]
