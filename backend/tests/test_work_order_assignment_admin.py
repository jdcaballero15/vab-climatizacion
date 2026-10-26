import uuid
from collections.abc import AsyncGenerator, Sequence
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.core.security import create_access_token
from app.db.models.catalog import EquipmentType, WorkType
from app.db.models.client import Client, ClientSite
from app.db.models.crew import Crew, FieldTechnician
from app.db.models.equipment import Equipment
from app.db.models.user import User, UserRole
from app.db.models.work_order import WorkOrder, WorkOrderAssignment, WorkOrderEvent
from app.db.session import SessionLocal, engine
from app.domain.work_order import OrderStatus, WorkOrderEventType
from app.main import app
from tests.factories import make_user, make_work_order

# E04-03: asignar una orden pendiente a una escuadrilla con fecha prevista (D-013).

TABLES = [
    User.__table__,
    Crew.__table__,
    FieldTechnician.__table__,
    Client.__table__,
    ClientSite.__table__,
    EquipmentType.__table__,
    Equipment.__table__,
    WorkType.__table__,
    WorkOrder.__table__,
    WorkOrderEvent.__table__,
    WorkOrderAssignment.__table__,
]
PENDING_URL = "/admin/orders?status=pending"
CREWS_URL = "/admin/crews"
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
        ):
            await conn.execute(text(f"DROP TYPE IF EXISTS {enum_type}"))
        await conn.execute(text("DROP SEQUENCE IF EXISTS work_order_number_seq"))


@pytest.fixture
async def admin(schema: None) -> User:
    user = make_user(email="admin@ot-demo.com", role=UserRole.admin, full_name="Admin Ficticio")
    await _seed([user])
    return user


@pytest.fixture
async def escuadrilla(schema: None) -> Crew:
    item = Crew(name="Escuadrilla 1")
    await _seed([item])
    return item


@pytest.fixture
async def sede(schema: None) -> ClientSite:
    cliente = Client(id=uuid.uuid4(), number="10642", name="Sanatorio Ficticio")
    await _seed([cliente])
    item = ClientSite(client_id=cliente.id, label="Central", address="Calle 1")
    await _seed([item])
    return item


@pytest.fixture
async def reparacion(schema: None) -> WorkType:
    item = WorkType(name="Reparación")
    await _seed([item])
    return item


@pytest.fixture
async def orden(sede: ClientSite, reparacion: WorkType) -> WorkOrder:
    return await _orden(sede, reparacion)


async def _orden(
    sede: ClientSite,
    tipo: WorkType,
    status: OrderStatus = OrderStatus.pending,
    *,
    requires_approval: bool = False,
) -> WorkOrder:
    item = make_work_order(client_site=sede, work_type=tipo, status=status)
    item.requires_approval = requires_approval
    await _seed([item])
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


def _url(order_id: object) -> str:
    return f"/admin/orders/{order_id}/assignment"


def _asignacion(crew_id: object, fecha: date | None = HOY) -> dict[str, object]:
    return {"crew_id": str(crew_id), "scheduled_for": fecha.isoformat() if fecha else None}


async def _asignar(user: User, order_id: object, payload: dict[str, object]) -> Response:
    async with _client() as client:
        return await client.post(_url(order_id), json=payload, headers=_auth(user))


def _code(response: Response) -> str:
    code: str = response.json()["detail"]["code"]
    return code


async def _estado(order_id: uuid.UUID) -> OrderStatus:
    async with SessionLocal() as session:
        status = await session.scalar(select(WorkOrder.status).where(WorkOrder.id == order_id))
    assert status is not None
    return status


async def _sin_asignacion_ni_evento() -> None:
    async with SessionLocal() as session:
        assert list(await session.scalars(select(WorkOrderAssignment))) == []
        assert list(await session.scalars(select(WorkOrderEvent))) == []


# Criterio 1: pasa a Asignada con esa escuadrilla como responsable.
async def test_asignar_pasa_a_asignada_con_la_escuadrilla(
    admin: User, escuadrilla: Crew, orden: WorkOrder
) -> None:
    manana = HOY + timedelta(days=1)
    response = await _asignar(admin, orden.id, _asignacion(escuadrilla.id, manana))

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["work_order_id"] == str(orden.id)
    assert body["crew_id"] == str(escuadrilla.id)
    assert body["scheduled_for"] == manana.isoformat()
    assert body["assigned_at"] is not None
    assert await _estado(orden.id) == OrderStatus.assigned

    async with SessionLocal() as session:
        asignaciones = list(await session.scalars(select(WorkOrderAssignment)))
    assert len(asignaciones) == 1
    assert asignaciones[0].crew_id == escuadrilla.id
    assert asignaciones[0].unassigned_at is None


# Criterio 2: evento con quién asignó, a qué escuadrilla y para qué fecha.
async def test_asignar_registra_el_evento(admin: User, escuadrilla: Crew, orden: WorkOrder) -> None:
    fecha = date(HOY.year + 1, 3, 5)
    await _asignar(admin, orden.id, _asignacion(escuadrilla.id, fecha))

    async with SessionLocal() as session:
        eventos = list(await session.scalars(select(WorkOrderEvent)))
    assert len(eventos) == 1
    evento = eventos[0]
    assert evento.event_type == WorkOrderEventType.assigned
    assert evento.from_status == OrderStatus.pending
    assert evento.to_status == OrderStatus.assigned
    assert evento.actor_id == admin.id
    assert evento.note == f"Escuadrilla: Escuadrilla 1. Fecha prevista: 05/03/{HOY.year + 1}."


async def test_la_fecha_de_hoy_se_acepta(admin: User, escuadrilla: Crew, orden: WorkOrder) -> None:
    response = await _asignar(admin, orden.id, _asignacion(escuadrilla.id, HOY))

    assert response.status_code == 201, response.text


async def test_escuadrilla_sin_celular_se_puede_asignar(
    admin: User, escuadrilla: Crew, orden: WorkOrder
) -> None:
    # El celular se asocia en E02-09; la asignación no lo exige.
    assert escuadrilla.app_user_id is None

    response = await _asignar(admin, orden.id, _asignacion(escuadrilla.id))

    assert response.status_code == 201, response.text


# Criterio 3: solo escuadrillas activas.
async def test_escuadrilla_inactiva_se_rechaza(admin: User, orden: WorkOrder) -> None:
    inactiva = Crew(name="Escuadrilla vieja", is_active=False)
    await _seed([inactiva])

    response = await _asignar(admin, orden.id, _asignacion(inactiva.id))

    assert response.status_code == 422
    assert _code(response) == "crew_not_available"
    await _sin_asignacion_ni_evento()
    assert await _estado(orden.id) == OrderStatus.pending


async def test_escuadrilla_inexistente_se_rechaza(admin: User, orden: WorkOrder) -> None:
    response = await _asignar(admin, orden.id, _asignacion(uuid.uuid4()))

    assert response.status_code == 422
    assert _code(response) == "crew_not_available"


async def test_mandar_un_tecnico_se_rechaza(admin: User, orden: WorkOrder) -> None:
    payload = {"technician_id": str(uuid.uuid4()), "scheduled_for": HOY.isoformat()}

    response = await _asignar(admin, orden.id, payload)

    assert response.status_code == 422


# Criterio 4: fecha anterior a hoy o sin fecha.
async def test_fecha_pasada_se_rechaza(admin: User, escuadrilla: Crew, orden: WorkOrder) -> None:
    ayer = HOY - timedelta(days=1)
    response = await _asignar(admin, orden.id, _asignacion(escuadrilla.id, ayer))

    assert response.status_code == 422
    assert _code(response) == "scheduled_date_in_past"
    await _sin_asignacion_ni_evento()


async def test_sin_fecha_se_rechaza(admin: User, escuadrilla: Crew, orden: WorkOrder) -> None:
    sin_fecha = await _asignar(admin, orden.id, _asignacion(escuadrilla.id, None))
    sin_campo = await _asignar(admin, orden.id, {"crew_id": str(escuadrilla.id)})

    assert sin_fecha.status_code == 422
    assert sin_campo.status_code == 422
    await _sin_asignacion_ni_evento()


# Criterio 5: una orden con aprobación pendiente no se asigna.
async def test_orden_que_requiere_aprobacion_se_rechaza(
    admin: User, escuadrilla: Crew, sede: ClientSite, reparacion: WorkType
) -> None:
    orden = await _orden(sede, reparacion, requires_approval=True)

    response = await _asignar(admin, orden.id, _asignacion(escuadrilla.id))

    assert response.status_code == 422
    assert _code(response) == "order_requires_approval"
    await _sin_asignacion_ni_evento()


# Criterio 6: una orden que no está Pendiente no se asigna (reasignar es E04-04).
@pytest.mark.parametrize(
    "estado", [OrderStatus.assigned, OrderStatus.in_progress, OrderStatus.cancelled]
)
async def test_orden_no_pendiente_se_rechaza(
    admin: User,
    escuadrilla: Crew,
    sede: ClientSite,
    reparacion: WorkType,
    estado: OrderStatus,
) -> None:
    orden = await _orden(sede, reparacion, estado)

    response = await _asignar(admin, orden.id, _asignacion(escuadrilla.id))

    assert response.status_code == 409
    assert _code(response) == "invalid_transition"
    assert await _estado(orden.id) == estado
    await _sin_asignacion_ni_evento()


async def test_orden_inexistente(admin: User, escuadrilla: Crew) -> None:
    response = await _asignar(admin, uuid.uuid4(), _asignacion(escuadrilla.id))

    assert response.status_code == 404
    assert _code(response) == "order_not_found"


# Criterio 7: al asignarla, sale del listado de pendientes.
async def test_la_asignada_sale_del_listado_de_pendientes(
    admin: User, escuadrilla: Crew, orden: WorkOrder
) -> None:
    async with SessionLocal() as session:
        session.add(
            WorkOrderEvent(
                work_order_id=orden.id,
                event_type=WorkOrderEventType.created,
                to_status=OrderStatus.pending,
            )
        )
        await session.commit()

    async with _client() as client:
        antes = await client.get(PENDING_URL, headers=_auth(admin))
        await client.post(_url(orden.id), json=_asignacion(escuadrilla.id), headers=_auth(admin))
        despues = await client.get(PENDING_URL, headers=_auth(admin))

    assert antes.json()["total"] == 1
    assert despues.json()["total"] == 0


# Una orden tiene una sola asignación vigente (una sola escuadrilla responsable, R7).
async def test_una_sola_asignacion_vigente_por_orden(escuadrilla: Crew, orden: WorkOrder) -> None:
    async with SessionLocal() as session:
        session.add_all(
            [
                WorkOrderAssignment(
                    work_order_id=orden.id, crew_id=escuadrilla.id, scheduled_for=HOY
                ),
                WorkOrderAssignment(
                    work_order_id=orden.id, crew_id=escuadrilla.id, scheduled_for=HOY
                ),
            ]
        )
        with pytest.raises(IntegrityError):
            await session.commit()


# Criterio 8: técnico (usuario de escuadrilla) y dirección reciben 403.
@pytest.mark.parametrize("rol", [UserRole.technician, UserRole.owner])
async def test_tecnico_y_direccion_no_asignan(
    escuadrilla: Crew, orden: WorkOrder, rol: UserRole
) -> None:
    usuario = make_user(email=f"{rol.value}@ot-demo.com", role=rol)
    await _seed([usuario])

    response = await _asignar(usuario, orden.id, _asignacion(escuadrilla.id))

    assert response.status_code == 403
    assert await _estado(orden.id) == OrderStatus.pending


# Criterio 9: no se desactiva una escuadrilla con órdenes Asignada o En curso.
@pytest.mark.parametrize("estado", [OrderStatus.assigned, OrderStatus.in_progress])
async def test_no_se_desactiva_con_ordenes_abiertas(
    admin: User,
    escuadrilla: Crew,
    sede: ClientSite,
    reparacion: WorkType,
    estado: OrderStatus,
) -> None:
    orden = await _orden(sede, reparacion, estado)
    await _seed(
        [WorkOrderAssignment(work_order_id=orden.id, crew_id=escuadrilla.id, scheduled_for=HOY)]
    )

    async with _client() as client:
        response = await client.patch(
            f"{CREWS_URL}/{escuadrilla.id}", json={"is_active": False}, headers=_auth(admin)
        )

    assert response.status_code == 409
    assert _code(response) == "crew_has_open_orders"
    async with SessionLocal() as session:
        sigue = await session.get(Crew, escuadrilla.id)
    assert sigue is not None and sigue.is_active


@pytest.mark.parametrize("estado", [OrderStatus.done, OrderStatus.cancelled])
async def test_se_desactiva_con_ordenes_cerradas(
    admin: User,
    escuadrilla: Crew,
    sede: ClientSite,
    reparacion: WorkType,
    estado: OrderStatus,
) -> None:
    orden = await _orden(sede, reparacion, estado)
    await _seed(
        [WorkOrderAssignment(work_order_id=orden.id, crew_id=escuadrilla.id, scheduled_for=HOY)]
    )

    async with _client() as client:
        response = await client.patch(
            f"{CREWS_URL}/{escuadrilla.id}", json={"is_active": False}, headers=_auth(admin)
        )

    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is False


async def test_renombrar_con_ordenes_abiertas_no_es_problema(
    admin: User, escuadrilla: Crew, orden: WorkOrder
) -> None:
    await _asignar(admin, orden.id, _asignacion(escuadrilla.id))

    async with _client() as client:
        response = await client.patch(
            f"{CREWS_URL}/{escuadrilla.id}", json={"name": "Escuadrilla Uno"}, headers=_auth(admin)
        )

    assert response.status_code == 200, response.text
