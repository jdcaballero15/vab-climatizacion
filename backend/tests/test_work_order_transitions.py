import uuid
from collections.abc import AsyncGenerator, Sequence

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.db.models.catalog import EquipmentType, WorkType
from app.db.models.client import Client, ClientSite
from app.db.models.equipment import Equipment
from app.db.models.user import User, UserRole
from app.db.models.work_order import WorkOrder, WorkOrderEvent
from app.db.session import SessionLocal, engine
from app.domain.work_order import (
    InvalidTransitionError,
    OrderAction,
    OrderStatus,
    ReasonRequiredError,
    TransitionRoleError,
    WorkOrderEventType,
)
from app.services import work_orders as service
from tests.factories import make_user, make_work_order

# E04-01: el servicio aplica las transiciones contra una base real.

TABLES = [
    User.__table__,
    Client.__table__,
    ClientSite.__table__,
    EquipmentType.__table__,
    Equipment.__table__,
    WorkType.__table__,
    WorkOrder.__table__,
    WorkOrderEvent.__table__,
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
        ):
            await conn.execute(text(f"DROP TYPE IF EXISTS {enum_type}"))
        await conn.execute(text("DROP SEQUENCE IF EXISTS work_order_number_seq"))


@pytest.fixture
async def admin(schema: None) -> User:
    user = make_user(email="admin@ot-demo.com", role=UserRole.admin)
    await _seed([user])
    return user


@pytest.fixture
async def tecnico(schema: None) -> User:
    user = make_user(email="tecnico@ot-demo.com", role=UserRole.technician)
    await _seed([user])
    return user


@pytest.fixture
async def orden(schema: None) -> WorkOrder:
    return await _nueva_orden(OrderStatus.pending)


async def _seed(items: Sequence[object]) -> None:
    async with SessionLocal() as session:
        session.add_all(list(items))
        await session.commit()


async def _nueva_orden(status: OrderStatus) -> WorkOrder:
    sufijo = uuid.uuid4().hex[:6]
    cliente = Client(id=uuid.uuid4(), number=f"T{sufijo}", name="Cliente Ficticio")
    sede = ClientSite(id=uuid.uuid4(), client_id=cliente.id, label="Sede", address="Calle 1")
    tipo = WorkType(id=uuid.uuid4(), name=f"Reparación {sufijo}")
    await _seed([cliente])
    await _seed([sede, tipo])
    orden = make_work_order(client_site=sede, work_type=tipo, status=status)
    await _seed([orden])
    return orden


async def _estado_y_eventos(order_id: uuid.UUID) -> tuple[OrderStatus, list[WorkOrderEvent]]:
    async with SessionLocal() as session:
        status = await session.scalar(select(WorkOrder.status).where(WorkOrder.id == order_id))
        result = await session.scalars(
            select(WorkOrderEvent).where(WorkOrderEvent.work_order_id == order_id)
        )
        assert status is not None
        return status, list(result)


async def _aplicar(
    order_id: uuid.UUID, action: OrderAction, actor: User, note: str | None = None
) -> WorkOrderEvent:
    async with SessionLocal() as session:
        order = await service.get_work_order(session, order_id)
        return await service.apply_transition(session, order, action, actor, note)


async def test_numero_sale_de_una_secuencia(schema: None) -> None:
    primera = await _nueva_orden(OrderStatus.pending)
    segunda = await _nueva_orden(OrderStatus.pending)
    assert segunda.number == primera.number + 1


# Criterio 3: evento con tipo, estados, usuario, fecha y nota, junto con el estado.
async def test_transicion_valida_actualiza_estado_e_inserta_evento(
    orden: WorkOrder, admin: User
) -> None:
    await _aplicar(orden.id, OrderAction.assign, admin, "Primera visita")

    status, eventos = await _estado_y_eventos(orden.id)
    assert status == OrderStatus.assigned
    assert len(eventos) == 1
    evento = eventos[0]
    assert evento.event_type == WorkOrderEventType.assigned
    assert evento.from_status == OrderStatus.pending
    assert evento.to_status == OrderStatus.assigned
    assert evento.actor_id == admin.id
    assert evento.occurred_at is not None
    assert evento.note == "Primera visita"


# Criterios 1 y 6: una transición inexistente o desde un estado final no modifica nada.
@pytest.mark.parametrize(
    ("origen", "accion"),
    [
        (OrderStatus.pending, OrderAction.invoice),
        (OrderStatus.paid, OrderAction.cancel),
        (OrderStatus.cancelled, OrderAction.assign),
    ],
)
async def test_transicion_invalida_no_modifica_nada(
    schema: None, admin: User, origen: OrderStatus, accion: OrderAction
) -> None:
    orden = await _nueva_orden(origen)

    with pytest.raises(InvalidTransitionError):
        await _aplicar(orden.id, accion, admin, "Motivo")

    status, eventos = await _estado_y_eventos(orden.id)
    assert status == origen
    assert eventos == []


# Criterio 2: administración no inicia una orden.
async def test_rol_equivocado_no_modifica_nada(schema: None, admin: User) -> None:
    orden = await _nueva_orden(OrderStatus.assigned)

    with pytest.raises(TransitionRoleError):
        await _aplicar(orden.id, OrderAction.start, admin)

    status, eventos = await _estado_y_eventos(orden.id)
    assert status == OrderStatus.assigned
    assert eventos == []


# Criterio 4: el motivo es obligatorio y queda en la nota del evento.
async def test_cancelar_sin_motivo_no_modifica_nada(orden: WorkOrder, admin: User) -> None:
    with pytest.raises(ReasonRequiredError):
        await _aplicar(orden.id, OrderAction.cancel, admin)

    status, eventos = await _estado_y_eventos(orden.id)
    assert status == OrderStatus.pending
    assert eventos == []


async def test_cancelar_con_motivo_guarda_el_motivo(orden: WorkOrder, admin: User) -> None:
    await _aplicar(orden.id, OrderAction.cancel, admin, "El cliente ya lo resolvió")

    status, eventos = await _estado_y_eventos(orden.id)
    assert status == OrderStatus.cancelled
    assert [e.note for e in eventos] == ["El cliente ya lo resolvió"]


async def test_el_tecnico_inicia_una_orden_asignada(schema: None, tecnico: User) -> None:
    orden = await _nueva_orden(OrderStatus.assigned)

    await _aplicar(orden.id, OrderAction.start, tecnico)

    status, eventos = await _estado_y_eventos(orden.id)
    assert status == OrderStatus.in_progress
    assert [e.actor_id for e in eventos] == [tecnico.id]


# Criterio 5: dos cambios simultáneos sobre la misma orden; solo uno gana.
async def test_cambio_simultaneo_da_conflicto_sin_evento_duplicado(
    orden: WorkOrder, admin: User
) -> None:
    async with SessionLocal() as primera, SessionLocal() as segunda:
        orden_a = await service.get_work_order(primera, orden.id)
        orden_b = await service.get_work_order(segunda, orden.id)

        await service.apply_transition(primera, orden_a, OrderAction.assign, admin, None)
        with pytest.raises(service.OrderStatusConflictError):
            await service.apply_transition(
                segunda, orden_b, OrderAction.cancel, admin, "Ya no hace falta"
            )

    status, eventos = await _estado_y_eventos(orden.id)
    assert status == OrderStatus.assigned
    assert len(eventos) == 1


# Criterio 7: un hecho que no cambia el estado queda como evento sin estado nuevo.
async def test_evento_sin_cambio_de_estado(schema: None, admin: User) -> None:
    orden = await _nueva_orden(OrderStatus.assigned)

    async with SessionLocal() as session:
        order = await service.get_work_order(session, orden.id)
        await service.record_event(
            session, order, WorkOrderEventType.reassigned, admin, "Pasa a otro técnico"
        )

    status, eventos = await _estado_y_eventos(orden.id)
    assert status == OrderStatus.assigned
    assert len(eventos) == 1
    assert eventos[0].event_type == WorkOrderEventType.reassigned
    assert eventos[0].to_status is None
    assert eventos[0].note == "Pasa a otro técnico"


async def test_registrar_un_cambio_de_estado_como_hecho_se_rechaza(
    orden: WorkOrder, admin: User
) -> None:
    async with SessionLocal() as session:
        order = await service.get_work_order(session, orden.id)
        with pytest.raises(ValueError, match="status_change"):
            await service.record_event(session, order, WorkOrderEventType.status_change, admin)

    async with SessionLocal() as session:
        total = await session.scalar(select(func.count()).select_from(WorkOrderEvent))
    assert total == 0


async def test_orden_inexistente(schema: None) -> None:
    async with SessionLocal() as session:
        with pytest.raises(service.WorkOrderNotFoundError):
            await service.get_work_order(session, uuid.uuid4())


async def test_tipo_de_evento_invalido_lo_rechaza_la_base(orden: WorkOrder) -> None:
    async with SessionLocal() as session:
        session.add(WorkOrderEvent(work_order_id=orden.id, event_type="inventado"))
        with pytest.raises(IntegrityError):
            await session.commit()
