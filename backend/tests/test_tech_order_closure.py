import uuid
from collections.abc import AsyncGenerator, Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import func, select, text

from app.core.security import create_access_token
from app.db.models.catalog import EquipmentType, Failure, Repair, Task, WorkType
from app.db.models.client import Client, ClientContact, ClientSite
from app.db.models.crew import Crew, FieldTechnician
from app.db.models.equipment import Equipment
from app.db.models.user import User, UserRole
from app.db.models.work_order import (
    WorkOrder,
    WorkOrderAssignment,
    WorkOrderClosure,
    WorkOrderClosureTask,
    WorkOrderClosureTechnician,
    WorkOrderEvent,
)
from app.db.session import SessionLocal, engine
from app.domain.work_order import OrderStatus, WorkOrderEventType
from app.main import app
from tests.factories import make_user, make_work_order

# E05-04, E05-08 y E05-12: cierre básico de una orden En curso desde el celular.

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
]
HOY = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).date()


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
        ):
            await conn.execute(text(f"DROP TYPE IF EXISTS {enum_type}"))
        await conn.execute(text("DROP SEQUENCE IF EXISTS work_order_number_seq"))


@dataclass
class Mundo:
    """Datos ficticios del cierre: escuadrillas, técnicos, catálogo y una sede."""

    celular: User
    escuadrilla: Crew
    otra_escuadrilla: Crew
    ana: FieldTechnician
    beto: FieldTechnician
    inactivo: FieldTechnician
    sede: ClientSite
    reparacion: WorkType
    instalacion: WorkType
    diagnosticar: Task
    probar: Task
    tarea_de_instalacion: Task
    split: EquipmentType
    heladera: EquipmentType
    no_enfria: Failure
    pierde_agua: Failure
    burlete: Failure
    falla_vieja: Failure
    carga_de_gas: Repair
    cambio_de_capacitor: Repair
    destapar_drenaje: Repair
    reparacion_vieja: Repair


@pytest.fixture
async def mundo(schema: None) -> Mundo:
    celular = make_user(email="esc1@ot-demo.com", role=UserRole.technician, full_name="Celular 1")
    await _seed([celular])
    escuadrilla = Crew(name="Escuadrilla 1", app_user_id=celular.id)
    otra = Crew(name="Escuadrilla 2")
    ana = FieldTechnician(full_name="Ana Ficticia")
    beto = FieldTechnician(full_name="Beto Ficticio")
    inactivo = FieldTechnician(full_name="Carlos Ficticio", is_active=False)
    cliente = Client(id=uuid.uuid4(), number="10642", name="Sanatorio Ficticio")
    reparacion = WorkType(name="Reparación", requires_failure_repair=True)
    instalacion = WorkType(name="Instalación")
    split = EquipmentType(name="Aire acondicionado")
    heladera = EquipmentType(name="Heladera comercial")
    await _seed([escuadrilla, otra, ana, beto, inactivo, cliente, reparacion, instalacion])
    await _seed([split, heladera])
    sede = ClientSite(client_id=cliente.id, label="Central", address="Calle 1")
    diagnosticar = Task(work_type_id=reparacion.id, name="Diagnosticar la falla")
    probar = Task(work_type_id=reparacion.id, name="Probar el funcionamiento")
    tarea_de_instalacion = Task(work_type_id=instalacion.id, name="Amurar soportes")
    no_enfria = Failure(name="No enfría")
    pierde_agua = Failure(name="Pierde agua", equipment_type_id=split.id)
    burlete = Failure(name="Burlete roto", equipment_type_id=heladera.id)
    falla_vieja = Failure(name="Falla vieja", is_active=False)
    await _seed([sede, diagnosticar, probar, tarea_de_instalacion, no_enfria, pierde_agua, burlete])
    await _seed([falla_vieja])
    carga_de_gas = Repair(name="Carga de gas", failure_id=no_enfria.id)
    cambio_de_capacitor = Repair(
        name="Cambio de capacitor", failure_id=no_enfria.id, equipment_type_id=split.id
    )
    destapar_drenaje = Repair(
        name="Destapar drenaje", failure_id=pierde_agua.id, equipment_type_id=split.id
    )
    reparacion_vieja = Repair(name="Reparación vieja", failure_id=no_enfria.id, is_active=False)
    await _seed([carga_de_gas, cambio_de_capacitor, destapar_drenaje, reparacion_vieja])
    return Mundo(
        celular=celular,
        escuadrilla=escuadrilla,
        otra_escuadrilla=otra,
        ana=ana,
        beto=beto,
        inactivo=inactivo,
        sede=sede,
        reparacion=reparacion,
        instalacion=instalacion,
        diagnosticar=diagnosticar,
        probar=probar,
        tarea_de_instalacion=tarea_de_instalacion,
        split=split,
        heladera=heladera,
        no_enfria=no_enfria,
        pierde_agua=pierde_agua,
        burlete=burlete,
        falla_vieja=falla_vieja,
        carga_de_gas=carga_de_gas,
        cambio_de_capacitor=cambio_de_capacitor,
        destapar_drenaje=destapar_drenaje,
        reparacion_vieja=reparacion_vieja,
    )


async def _orden(
    m: Mundo,
    tipo: WorkType | None = None,
    status: OrderStatus = OrderStatus.in_progress,
    *,
    crew: Crew | None = None,
    equipment: Equipment | None = None,
) -> WorkOrder:
    item = make_work_order(client_site=m.sede, work_type=tipo or m.reparacion, status=status)
    item.description = "Cámara no enfría"
    if equipment is not None:
        item.equipment_id = equipment.id
    await _seed([item])
    await _seed(
        [
            WorkOrderAssignment(
                work_order_id=item.id, crew_id=(crew or m.escuadrilla).id, scheduled_for=HOY
            )
        ]
    )
    return item


async def _equipo_split(m: Mundo) -> Equipment:
    equipo = Equipment(
        client_site_id=m.sede.id,
        equipment_type_id=m.split.id,
        internal_code="EA1064201",
        location_note="Habitación 12",
    )
    await _seed([equipo])
    return equipo


async def _seed(items: Sequence[object]) -> None:
    async with SessionLocal() as session:
        session.add_all(list(items))
        await session.commit()


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _opciones(user: User, order_id: object) -> Response:
    async with _client() as client:
        return await client.get(f"/tech/orders/{order_id}/closure-options", headers=_auth(user))


async def _cerrar(user: User, order_id: object, payload: dict[str, Any]) -> Response:
    async with _client() as client:
        return await client.post(
            f"/tech/orders/{order_id}/closure", json=payload, headers=_auth(user)
        )


def _resuelta(m: Mundo, **cambios: Any) -> dict[str, Any]:
    """Cierre "Resuelta" completo y válido para una orden de reparación sin equipo."""
    payload: dict[str, Any] = {
        "idempotency_key": str(uuid.uuid4()),
        "outcome": "done",
        "technician_ids": [str(m.ana.id), str(m.beto.id)],
        "task_ids": [str(m.diagnosticar.id)],
        "failure_id": str(m.no_enfria.id),
        "failure_other_text": None,
        "repair_id": str(m.carga_de_gas.id),
        "repair_other_text": None,
        "equipment_condition": "working",
        "not_done_reason": None,
        "observation": None,
    }
    payload.update(cambios)
    return payload


async def _leer(order_id: uuid.UUID) -> tuple[OrderStatus, list[WorkOrderEvent], int]:
    async with SessionLocal() as session:
        status = await session.scalar(select(WorkOrder.status).where(WorkOrder.id == order_id))
        eventos = (
            await session.execute(
                select(WorkOrderEvent)
                .where(WorkOrderEvent.work_order_id == order_id)
                .order_by(WorkOrderEvent.occurred_at)
            )
        ).scalars()
        cierres = await session.scalar(
            select(func.count())
            .select_from(WorkOrderClosure)
            .where(WorkOrderClosure.work_order_id == order_id)
        )
        assert status is not None
        return status, list(eventos), cierres or 0


def _detail(response: Response) -> dict[str, Any]:
    detail: dict[str, Any] = response.json()["detail"]
    return detail


# ---- Opciones del cierre (E05-04, criterios 2 a 5) ----


async def test_opciones_de_una_orden_sin_equipo(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m)

    response = await _opciones(m.celular, orden.id)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["technicians"] == [
        {"id": str(m.ana.id), "name": "Ana Ficticia"},
        {"id": str(m.beto.id), "name": "Beto Ficticio"},
    ]
    assert body["tasks"] == [
        {"id": str(m.diagnosticar.id), "name": "Diagnosticar la falla"},
        {"id": str(m.probar.id), "name": "Probar el funcionamiento"},
    ]
    assert body["requires_failure_repair"] is True
    # Sin equipo: solo genéricas y activas, también entre las reparaciones.
    assert body["failures"] == [
        {
            "id": str(m.no_enfria.id),
            "name": "No enfría",
            "repairs": [{"id": str(m.carga_de_gas.id), "name": "Carga de gas"}],
        }
    ]


async def test_opciones_con_equipo_suman_las_de_su_tipo(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m, equipment=await _equipo_split(m))

    body = (await _opciones(m.celular, orden.id)).json()

    assert body["failures"] == [
        {
            "id": str(m.no_enfria.id),
            "name": "No enfría",
            "repairs": [
                {"id": str(m.cambio_de_capacitor.id), "name": "Cambio de capacitor"},
                {"id": str(m.carga_de_gas.id), "name": "Carga de gas"},
            ],
        },
        {
            "id": str(m.pierde_agua.id),
            "name": "Pierde agua",
            "repairs": [{"id": str(m.destapar_drenaje.id), "name": "Destapar drenaje"}],
        },
    ]


async def test_opciones_de_un_tipo_sin_falla(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m, m.instalacion)

    body = (await _opciones(m.celular, orden.id)).json()

    assert body["requires_failure_repair"] is False
    assert body["tasks"] == [{"id": str(m.tarea_de_instalacion.id), "name": "Amurar soportes"}]


@pytest.mark.parametrize(
    ("status", "de_otra"),
    [(OrderStatus.assigned, False), (OrderStatus.done, False), (OrderStatus.in_progress, True)],
    ids=["asignada", "terminada", "otra-escuadrilla"],
)
async def test_opciones_de_una_orden_que_no_esta_en_curso_dan_404(
    mundo: Mundo, status: OrderStatus, de_otra: bool
) -> None:
    m = mundo
    orden = await _orden(m, status=status, crew=m.otra_escuadrilla if de_otra else None)

    response = await _opciones(m.celular, orden.id)

    assert response.status_code == 404
    assert _detail(response)["code"] == "order_not_found"


# ---- Cierre: resultados (E05-08) ----


# E05-08, criterio 2 y E05-04, criterios 2 a 4 y 7: Resuelta pasa a Terminada y guarda todo.
async def test_cerrar_resuelta_pasa_a_terminada_y_guarda_el_cierre(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m)
    payload = _resuelta(m)

    response = await _cerrar(m.celular, orden.id, payload)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["outcome"] == "done"
    assert body["order_status"] == "done"
    status, eventos, cierres = await _leer(orden.id)
    assert status == OrderStatus.done
    assert cierres == 1
    (evento,) = eventos
    assert evento.from_status == OrderStatus.in_progress
    assert evento.to_status == OrderStatus.done
    assert evento.actor_id == m.celular.id
    assert evento.note == "Resuelta."
    async with SessionLocal() as session:
        cierre = await session.scalar(select(WorkOrderClosure))
        assert cierre is not None
        assert str(cierre.id) == body["id"]
        assert cierre.closed_by == m.celular.id
        assert cierre.failure_id == m.no_enfria.id
        assert cierre.repair_id == m.carga_de_gas.id
        assert cierre.equipment_condition == "working"
        assert str(cierre.idempotency_key) == payload["idempotency_key"]
        tecnicos = set(
            (await session.execute(select(WorkOrderClosureTechnician.field_technician_id)))
            .scalars()
            .all()
        )
        tareas = (await session.execute(select(WorkOrderClosureTask.task_id))).scalars().all()
    assert tecnicos == {m.ana.id, m.beto.id}
    # E05-04, criterio 3: se cierra aunque falte una tarea; queda la que se tildó.
    assert list(tareas) == [m.diagnosticar.id]


# E05-08, criterio 3: otra visita vuelve a Pendiente sin escuadrilla.
async def test_otra_visita_vuelve_a_pendiente_sin_escuadrilla(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m)

    response = await _cerrar(
        m.celular,
        orden.id,
        _resuelta(m, outcome="needs_revisit", observation="Falta el capacitor."),
    )

    assert response.status_code == 201, response.text
    assert response.json()["order_status"] == "pending"
    status, eventos, _ = await _leer(orden.id)
    assert status == OrderStatus.pending
    assert eventos[-1].note == "Requiere otra visita: Falta el capacitor."
    async with SessionLocal() as session:
        asignacion = await session.scalar(select(WorkOrderAssignment))
        assert asignacion is not None
        assert asignacion.unassigned_at is not None


# E05-08, criterio 4: no se pudo hacer, con motivo; no pide falla ni estado del equipo.
async def test_no_se_pudo_hacer_vuelve_a_pendiente_con_motivo(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m)

    response = await _cerrar(
        m.celular,
        orden.id,
        _resuelta(
            m,
            outcome="not_done",
            not_done_reason="client_absent",
            failure_id=None,
            repair_id=None,
            equipment_condition=None,
            task_ids=[],
        ),
    )

    assert response.status_code == 201, response.text
    status, eventos, _ = await _leer(orden.id)
    assert status == OrderStatus.pending
    assert eventos[-1].note == "No se pudo hacer: Cliente ausente o sin acceso."
    async with SessionLocal() as session:
        asignacion = await session.scalar(select(WorkOrderAssignment))
        assert asignacion is not None
        assert asignacion.unassigned_at is not None


# ---- Motivo en el listado de pendientes (E05-08, criterio 5) ----


async def _pendientes(*ordenes: WorkOrder) -> dict[int, dict[str, Any] | None]:
    """El campo returned de cada orden pendiente, por número.

    El listado ordena por el evento de creación, que las órdenes de prueba no traen.
    """
    await _seed(
        [
            WorkOrderEvent(
                work_order_id=orden.id,
                event_type=WorkOrderEventType.created,
                to_status=OrderStatus.pending,
            )
            for orden in ordenes
        ]
    )
    admin = make_user(email="admin@ot-demo.com", role=UserRole.admin, full_name="Admin")
    await _seed([admin])
    async with _client() as client:
        response = await client.get("/admin/orders?status=pending", headers=_auth(admin))
    assert response.status_code == 200, response.text
    return {item["number"]: item["returned"] for item in response.json()["items"]}


async def test_pendientes_muestran_por_que_volvio_de_la_escuadrilla(mundo: Mundo) -> None:
    m = mundo
    otra_visita = await _orden(m)
    no_se_pudo = await _orden(m)
    nueva = make_work_order(client_site=m.sede, work_type=m.reparacion)
    await _seed([nueva])
    await _cerrar(
        m.celular,
        otra_visita.id,
        _resuelta(m, outcome="needs_revisit", observation="Falta el capacitor."),
    )
    await _cerrar(
        m.celular,
        no_se_pudo.id,
        _resuelta(
            m,
            outcome="not_done",
            not_done_reason="client_absent",
            failure_id=None,
            repair_id=None,
            equipment_condition=None,
            task_ids=[],
        ),
    )

    pendientes = await _pendientes(otra_visita, no_se_pudo, nueva)

    assert pendientes[nueva.number] is None
    vuelta = pendientes[otra_visita.number]
    assert vuelta is not None
    assert vuelta["crew_name"] == "Escuadrilla 1"
    assert vuelta["outcome"] == "needs_revisit"
    assert vuelta["not_done_reason"] is None
    assert vuelta["observation"] == "Falta el capacitor."
    assert vuelta["closed_at"]
    vuelta = pendientes[no_se_pudo.number]
    assert vuelta is not None
    assert vuelta["outcome"] == "not_done"
    assert vuelta["not_done_reason"] == "client_absent"


async def test_pendiente_reasignada_y_desasignada_no_muestra_el_cierre_viejo(
    mundo: Mundo,
) -> None:
    m = mundo
    orden = await _orden(m)
    await _cerrar(
        m.celular,
        orden.id,
        _resuelta(m, outcome="needs_revisit", observation="Falta el capacitor."),
    )
    # La oficina la asigna a otra escuadrilla y después la desasigna (vuelve a Pendiente).
    async with SessionLocal() as session:
        session.add(
            WorkOrderAssignment(
                work_order_id=orden.id,
                crew_id=m.otra_escuadrilla.id,
                scheduled_for=HOY,
                unassigned_at=func.now(),
            )
        )
        await session.commit()

    assert (await _pendientes(orden))[orden.number] is None


# E05-04, criterio 4: un tipo que no pide falla se cierra como resuelta sin ella.
async def test_tipo_sin_falla_se_cierra_sin_falla_ni_reparacion(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m, m.instalacion)

    response = await _cerrar(
        m.celular,
        orden.id,
        _resuelta(m, failure_id=None, repair_id=None, task_ids=[str(m.tarea_de_instalacion.id)]),
    )

    assert response.status_code == 201, response.text


# E05-04, criterio 6: "Otro" con texto y observación.
async def test_falla_y_reparacion_otro_con_observacion(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m)

    response = await _cerrar(
        m.celular,
        orden.id,
        _resuelta(
            m,
            failure_id=None,
            failure_other_text="Ruido en el ventilador",
            repair_id=None,
            repair_other_text="Ajuste de paletas",
            observation="El ventilador rozaba la carcasa.",
        ),
    )

    assert response.status_code == 201, response.text
    async with SessionLocal() as session:
        cierre = await session.scalar(select(WorkOrderClosure))
        assert cierre is not None
        assert cierre.failure_other_text == "Ruido en el ventilador"
        assert cierre.repair_other_text == "Ajuste de paletas"


# E05-04, criterio 5: con equipo se aceptan las fallas de su tipo.
async def test_falla_del_tipo_de_equipo_de_la_orden(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m, equipment=await _equipo_split(m))

    response = await _cerrar(
        m.celular,
        orden.id,
        _resuelta(m, failure_id=str(m.pierde_agua.id), repair_id=str(m.destapar_drenaje.id)),
    )

    assert response.status_code == 201, response.text


# ---- Validaciones (E05-04, criterio 8) ----


def _sin(m: Mundo, campo: str, valor: Any = None) -> dict[str, Any]:
    return _resuelta(m, **{campo: valor})


VALIDACIONES: list[tuple[str, Callable[[Mundo], dict[str, Any]], str, str]] = [
    (
        "sin-tecnicos",
        lambda m: _sin(m, "technician_ids", []),
        "technicians_required",
        "technician_ids",
    ),
    (
        "tecnico-inactivo",
        lambda m: _resuelta(m, technician_ids=[str(m.inactivo.id)]),
        "technician_not_available",
        "technician_ids",
    ),
    (
        "tarea-de-otro-tipo",
        lambda m: _resuelta(m, task_ids=[str(m.tarea_de_instalacion.id)]),
        "task_not_available",
        "task_ids",
    ),
    (
        "sin-falla",
        lambda m: _resuelta(m, failure_id=None, repair_id=None),
        "failure_required",
        "failure_id",
    ),
    ("sin-reparacion", lambda m: _sin(m, "repair_id"), "repair_required", "repair_id"),
    (
        "falla-de-otro-tipo",
        lambda m: _resuelta(m, failure_id=str(m.burlete.id), repair_id=None),
        "failure_not_available",
        "failure_id",
    ),
    (
        "falla-especifica-sin-equipo",
        lambda m: _resuelta(m, failure_id=str(m.pierde_agua.id), repair_id=None),
        "failure_not_available",
        "failure_id",
    ),
    (
        "falla-inactiva",
        lambda m: _resuelta(m, failure_id=str(m.falla_vieja.id), repair_id=None),
        "failure_not_available",
        "failure_id",
    ),
    (
        "reparacion-de-otra-falla",
        lambda m: _resuelta(m, repair_id=str(m.destapar_drenaje.id)),
        "repair_not_available",
        "repair_id",
    ),
    (
        "reparacion-inactiva",
        lambda m: _resuelta(m, repair_id=str(m.reparacion_vieja.id)),
        "repair_not_available",
        "repair_id",
    ),
    (
        "reparacion-sin-falla",
        lambda m: _resuelta(m, outcome="needs_revisit", observation="x", failure_id=None),
        "repair_without_failure",
        "repair_id",
    ),
    (
        "falla-con-id-y-otro",
        lambda m: _resuelta(m, failure_other_text="Otra cosa", observation="x"),
        "failure_ambiguous",
        "failure_id",
    ),
    (
        "reparacion-con-id-y-otro",
        lambda m: _resuelta(m, repair_other_text="Otra cosa", observation="x"),
        "repair_ambiguous",
        "repair_id",
    ),
    (
        "reparacion-de-catalogo-con-falla-otro",
        lambda m: _resuelta(m, failure_id=None, failure_other_text="Otra", observation="x"),
        "repair_not_available",
        "repair_id",
    ),
    (
        "otro-sin-observacion",
        lambda m: _resuelta(
            m, failure_id=None, failure_other_text="Otra", repair_id=None, repair_other_text="Otra"
        ),
        "observation_required",
        "observation",
    ),
    (
        "sin-estado-del-equipo",
        lambda m: _sin(m, "equipment_condition"),
        "equipment_condition_required",
        "equipment_condition",
    ),
    (
        "con-observaciones-sin-observacion",
        lambda m: _resuelta(m, equipment_condition="working_with_notes"),
        "observation_required",
        "observation",
    ),
    (
        "otra-visita-sin-observacion",
        lambda m: _resuelta(m, outcome="needs_revisit"),
        "observation_required",
        "observation",
    ),
    (
        "no-se-pudo-sin-motivo",
        lambda m: _resuelta(m, outcome="not_done", failure_id=None, repair_id=None),
        "not_done_reason_required",
        "not_done_reason",
    ),
    (
        "motivo-sin-no-se-pudo",
        lambda m: _resuelta(m, not_done_reason="missing_part"),
        "not_done_reason_not_allowed",
        "not_done_reason",
    ),
]


@pytest.mark.parametrize(
    ("armar", "code", "field"),
    [(armar, code, field) for _, armar, code, field in VALIDACIONES],
    ids=[nombre for nombre, *_ in VALIDACIONES],
)
async def test_cierre_incompleto_se_rechaza_con_el_campo(
    mundo: Mundo, armar: Callable[[Mundo], dict[str, Any]], code: str, field: str
) -> None:
    m = mundo
    orden = await _orden(m)

    response = await _cerrar(m.celular, orden.id, armar(m))

    assert response.status_code == 422, response.text
    assert _detail(response)["code"] == code
    assert _detail(response)["field"] == field
    status, eventos, cierres = await _leer(orden.id)
    assert (status, eventos, cierres) == (OrderStatus.in_progress, [], 0)


async def test_resultado_retiro_todavia_no_se_acepta(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m)

    response = await _cerrar(m.celular, orden.id, _resuelta(m, outcome="needs_pickup"))

    assert response.status_code == 422


# ---- Idempotencia (E05-12) ----


# Criterios 1 y 2: la misma clave devuelve el cierre original sin repetir efectos.
async def test_mismo_cierre_dos_veces_no_se_duplica(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m)
    payload = _resuelta(m)

    primera = await _cerrar(m.celular, orden.id, payload)
    segunda = await _cerrar(m.celular, orden.id, payload)

    assert primera.status_code == 201
    assert segunda.status_code == 200
    assert segunda.json() == primera.json()
    _, eventos, cierres = await _leer(orden.id)
    assert cierres == 1
    assert len(eventos) == 1


# Criterio 3: un segundo cierre con otra clave se rechaza: la orden ya no está En curso.
async def test_otro_cierre_de_una_orden_cerrada_se_rechaza(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m)
    await _cerrar(m.celular, orden.id, _resuelta(m))

    response = await _cerrar(m.celular, orden.id, _resuelta(m))

    assert response.status_code == 404
    _, _, cierres = await _leer(orden.id)
    assert cierres == 1


async def test_clave_usada_en_otra_orden_se_rechaza(mundo: Mundo) -> None:
    m = mundo
    primera = await _orden(m)
    segunda = await _orden(m)
    payload = _resuelta(m)
    await _cerrar(m.celular, primera.id, payload)

    response = await _cerrar(m.celular, segunda.id, payload)

    assert response.status_code == 422
    assert _detail(response)["code"] == "idempotency_key_reused"


# ---- Acceso (E05-04, criterio 10) ----


@pytest.mark.parametrize(
    ("status", "de_otra"),
    [(OrderStatus.assigned, False), (OrderStatus.pending, False), (OrderStatus.in_progress, True)],
    ids=["asignada", "pendiente", "otra-escuadrilla"],
)
async def test_cerrar_una_orden_que_no_esta_en_curso_da_404(
    mundo: Mundo, status: OrderStatus, de_otra: bool
) -> None:
    m = mundo
    orden = await _orden(m, status=status, crew=m.otra_escuadrilla if de_otra else None)

    response = await _cerrar(m.celular, orden.id, _resuelta(m))

    assert response.status_code == 404
    _, _, cierres = await _leer(orden.id)
    assert cierres == 0


@pytest.mark.parametrize("role", [UserRole.admin, UserRole.owner])
async def test_otros_roles_reciben_403(mundo: Mundo, role: UserRole) -> None:
    m = mundo
    orden = await _orden(m)
    user = make_user(email=f"{role.value}@ot-demo.com", role=role)
    await _seed([user])

    assert (await _opciones(user, orden.id)).status_code == 403
    assert (await _cerrar(user, orden.id, _resuelta(m))).status_code == 403
