import uuid
from collections.abc import AsyncGenerator, Sequence
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select, text

from app.core.security import create_access_token
from app.db.models.catalog import EquipmentType, Task, WorkType
from app.db.models.client import Client, ClientContact, ClientSite
from app.db.models.crew import Crew
from app.db.models.equipment import Equipment
from app.db.models.user import User, UserRole
from app.db.models.work_order import WorkOrder, WorkOrderAssignment, WorkOrderEvent
from app.db.session import SessionLocal, engine
from app.domain.work_order import OrderStatus
from app.main import app
from app.services import work_orders as work_orders_service
from tests.factories import make_user, make_work_order

# E05-03: la escuadrilla inicia una de sus órdenes (Asignada -> En curso).

TABLES = [
    User.__table__,
    Crew.__table__,
    Client.__table__,
    ClientSite.__table__,
    ClientContact.__table__,
    EquipmentType.__table__,
    Equipment.__table__,
    WorkType.__table__,
    Task.__table__,
    WorkOrder.__table__,
    WorkOrderEvent.__table__,
    WorkOrderAssignment.__table__,
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
        ):
            await conn.execute(text(f"DROP TYPE IF EXISTS {enum_type}"))
        await conn.execute(text("DROP SEQUENCE IF EXISTS work_order_number_seq"))


@pytest.fixture
async def celular(schema: None) -> User:
    user = make_user(email="esc1@ot-demo.com", role=UserRole.technician, full_name="Celular 1")
    await _seed([user])
    return user


@pytest.fixture
async def escuadrilla(celular: User) -> Crew:
    item = Crew(name="Escuadrilla 1", app_user_id=celular.id)
    await _seed([item])
    return item


@pytest.fixture
async def otra_escuadrilla(schema: None) -> Crew:
    item = Crew(name="Escuadrilla 2")
    await _seed([item])
    return item


@pytest.fixture
async def sede(schema: None) -> ClientSite:
    cliente = Client(id=uuid.uuid4(), number="10642", name="Sanatorio Ficticio")
    await _seed([cliente])
    item = ClientSite(
        client_id=cliente.id, label="Central", address="Calle 1", reference="Portón verde"
    )
    await _seed([item])
    await _seed(
        [
            ClientContact(
                client_id=cliente.id,
                client_site_id=item.id,
                name="Marta Ficticia",
                phone="3850000000",
                email="marta@ficticio.com",
            )
        ]
    )
    return item


@pytest.fixture
async def reparacion(schema: None) -> WorkType:
    item = WorkType(name="Reparación")
    await _seed([item])
    await _seed(
        [
            Task(work_type_id=item.id, name="Probar el funcionamiento"),
            Task(work_type_id=item.id, name="Diagnosticar la falla"),
            Task(work_type_id=item.id, name="Tarea vieja", is_active=False),
        ]
    )
    return item


async def _orden(
    sede: ClientSite,
    tipo: WorkType,
    crew: Crew | None,
    status: OrderStatus = OrderStatus.assigned,
    *,
    unassigned: bool = False,
    equipment: Equipment | None = None,
    scheduled_for: object = HOY,
) -> WorkOrder:
    item = make_work_order(client_site=sede, work_type=tipo, status=status)
    item.description = "Cámara no enfría. Mercadería en riesgo: ir primero."
    item.requester_name = "Encargado Ficticio"
    item.requester_area = "Planta baja"
    if equipment is not None:
        item.equipment_id = equipment.id
    await _seed([item])
    if crew is not None:
        await _seed(
            [
                WorkOrderAssignment(
                    work_order_id=item.id,
                    crew_id=crew.id,
                    scheduled_for=scheduled_for,
                    unassigned_at=datetime.now(ZoneInfo("UTC")) if unassigned else None,
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


async def _start(user: User, order_id: object) -> Response:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.post(f"/tech/orders/{order_id}/start", headers=_auth(user))


async def _estado_y_eventos(order_id: uuid.UUID) -> tuple[OrderStatus, list[WorkOrderEvent]]:
    async with SessionLocal() as session:
        status = await session.scalar(select(WorkOrder.status).where(WorkOrder.id == order_id))
        result = await session.execute(
            select(WorkOrderEvent).where(WorkOrderEvent.work_order_id == order_id)
        )
        assert status is not None
        return status, list(result.scalars().all())


# Criterio 2: pasa a En curso con un evento del usuario de la escuadrilla.
async def test_iniciar_pasa_a_en_curso_con_evento(
    celular: User, escuadrilla: Crew, sede: ClientSite, reparacion: WorkType
) -> None:
    orden = await _orden(sede, reparacion, escuadrilla)

    response = await _start(celular, orden.id)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(orden.id)
    assert body["status"] == "in_progress"
    assert body["tasks"] == ["Diagnosticar la falla", "Probar el funcionamiento"]
    status, eventos = await _estado_y_eventos(orden.id)
    assert status == OrderStatus.in_progress
    (evento,) = eventos
    assert evento.event_type == "status_change"
    assert evento.from_status == OrderStatus.assigned
    assert evento.to_status == OrderStatus.in_progress
    assert evento.actor_id == celular.id
    assert evento.occurred_at is not None


# Criterio 3: iniciar de nuevo no cambia nada ni duplica el evento.
async def test_iniciar_dos_veces_no_duplica_el_evento(
    celular: User, escuadrilla: Crew, sede: ClientSite, reparacion: WorkType
) -> None:
    orden = await _orden(sede, reparacion, escuadrilla)

    primera = await _start(celular, orden.id)
    segunda = await _start(celular, orden.id)

    assert primera.status_code == segunda.status_code == 200
    assert segunda.json()["status"] == "in_progress"
    _, eventos = await _estado_y_eventos(orden.id)
    assert len(eventos) == 1


# Criterio 4: lo que no es una orden abierta de mi escuadrilla da 404 y no cambia.
@pytest.mark.parametrize(
    ("de_otra", "status", "unassigned"),
    [
        (True, OrderStatus.assigned, False),
        (False, OrderStatus.done, False),
        (False, OrderStatus.cancelled, False),
        (False, OrderStatus.assigned, True),
    ],
    ids=["otra-escuadrilla", "terminada", "cancelada", "desasignada"],
)
async def test_orden_que_no_es_abierta_de_mi_escuadrilla_da_404(
    celular: User,
    escuadrilla: Crew,
    otra_escuadrilla: Crew,
    sede: ClientSite,
    reparacion: WorkType,
    de_otra: bool,
    status: OrderStatus,
    unassigned: bool,
) -> None:
    crew = otra_escuadrilla if de_otra else escuadrilla
    orden = await _orden(sede, reparacion, crew, status, unassigned=unassigned)

    response = await _start(celular, orden.id)

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "order_not_found"
    estado, eventos = await _estado_y_eventos(orden.id)
    assert estado == status
    assert eventos == []


async def test_id_inexistente_da_404(celular: User, escuadrilla: Crew) -> None:
    assert (await _start(celular, uuid.uuid4())).status_code == 404


# Criterio 5: una orden prevista para otro día se puede iniciar.
async def test_se_puede_iniciar_una_orden_de_otro_dia(
    celular: User, escuadrilla: Crew, sede: ClientSite, reparacion: WorkType
) -> None:
    orden = await _orden(sede, reparacion, escuadrilla, scheduled_for=HOY + timedelta(days=3))
    assert (await _start(celular, orden.id)).json()["status"] == "in_progress"


# Criterio 6: varias en curso a la vez.
async def test_puede_tener_varias_en_curso(
    celular: User, escuadrilla: Crew, sede: ClientSite, reparacion: WorkType
) -> None:
    en_curso = await _orden(sede, reparacion, escuadrilla, OrderStatus.in_progress)
    orden = await _orden(sede, reparacion, escuadrilla)

    assert (await _start(celular, orden.id)).json()["status"] == "in_progress"
    estado, _ = await _estado_y_eventos(en_curso.id)
    assert estado == OrderStatus.in_progress


# Criterio 7: administración y dirección reciben 403.
@pytest.mark.parametrize("role", [UserRole.admin, UserRole.owner])
async def test_otros_roles_reciben_403(schema: None, role: UserRole) -> None:
    user = make_user(email=f"{role.value}@ot-demo.com", role=role)
    await _seed([user])
    assert (await _start(user, uuid.uuid4())).status_code == 403


async def _cambiar_estado_antes(
    monkeypatch: pytest.MonkeyPatch, order_id: uuid.UUID, nuevo: OrderStatus
) -> None:
    """Simula otra petición que cambia el estado entre la lectura y la transición."""
    original = work_orders_service.apply_transition

    async def con_carrera(*args: Any, **kwargs: Any) -> Any:
        async with SessionLocal() as otra:
            await otra.execute(
                text("UPDATE work_order SET status = :s WHERE id = :id"),
                {"s": nuevo.value, "id": order_id},
            )
            await otra.commit()
        return await original(*args, **kwargs)

    monkeypatch.setattr(work_orders_service, "apply_transition", con_carrera)


# Criterio 3: dos toques que llegan a la vez dan el mismo resultado, sin error.
async def test_doble_toque_simultaneo_responde_bien(
    monkeypatch: pytest.MonkeyPatch,
    celular: User,
    escuadrilla: Crew,
    sede: ClientSite,
    reparacion: WorkType,
) -> None:
    orden = await _orden(sede, reparacion, escuadrilla)
    await _cambiar_estado_antes(monkeypatch, orden.id, OrderStatus.in_progress)

    response = await _start(celular, orden.id)

    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


# Si mientras tanto la cancelaron, ya no es de la escuadrilla: 404, como en el detalle.
async def test_cancelada_mientras_se_iniciaba_da_404(
    monkeypatch: pytest.MonkeyPatch,
    celular: User,
    escuadrilla: Crew,
    sede: ClientSite,
    reparacion: WorkType,
) -> None:
    orden = await _orden(sede, reparacion, escuadrilla)
    await _cambiar_estado_antes(monkeypatch, orden.id, OrderStatus.cancelled)

    response = await _start(celular, orden.id)

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "order_not_found"
