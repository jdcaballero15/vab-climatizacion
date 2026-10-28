import uuid
from collections.abc import AsyncGenerator, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import text

from app.core.security import create_access_token
from app.db.models.catalog import EquipmentType, Failure, Repair, WorkType
from app.db.models.client import Client, ClientContact, ClientSite
from app.db.models.crew import Crew
from app.db.models.equipment import Equipment
from app.db.models.user import User, UserRole
from app.db.models.work_order import (
    WorkOrder,
    WorkOrderAssignment,
    WorkOrderClosure,
    WorkOrderEvent,
)
from app.db.session import SessionLocal, engine
from app.domain.work_order import ClosureOutcome, NotDoneReason, OrderStatus
from app.main import app
from tests.factories import make_user, make_work_order

# E05-14: la escuadrilla ve en el celular los cierres que hizo en los últimos 7 días.

TABLES = [
    User.__table__,
    Crew.__table__,
    Client.__table__,
    ClientSite.__table__,
    ClientContact.__table__,
    EquipmentType.__table__,
    Equipment.__table__,
    WorkType.__table__,
    Failure.__table__,
    Repair.__table__,
    WorkOrder.__table__,
    WorkOrderEvent.__table__,
    WorkOrderAssignment.__table__,
    WorkOrderClosure.__table__,
]
URL = "/tech/orders/done"
AHORA = datetime.now(UTC)


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
            "no_signature_reason",
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
    user = make_user(email="esc2@ot-demo.com", role=UserRole.technician, full_name="Celular 2")
    await _seed([user])
    item = Crew(name="Escuadrilla 2", app_user_id=user.id)
    await _seed([item])
    return item


@pytest.fixture
async def sede(schema: None) -> ClientSite:
    cliente = Client(id=uuid.uuid4(), number="10642", name="Sanatorio Ficticio")
    await _seed([cliente])
    item = ClientSite(client_id=cliente.id, label="Central", address="Calle 1")
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
    return item


async def _orden(
    sede: ClientSite, tipo: WorkType, status: OrderStatus = OrderStatus.done
) -> WorkOrder:
    item = make_work_order(client_site=sede, work_type=tipo, status=status)
    item.description = "Cámara no enfría"
    item.requester_name = "Encargado Ficticio"
    await _seed([item])
    return item


async def _asignar(
    orden: WorkOrder, crew: Crew, hace: timedelta, hasta: timedelta | None = None
) -> None:
    """Asignación desde `hace`; con `hasta`, ya terminada (hay una sola vigente por orden)."""
    await _seed(
        [
            WorkOrderAssignment(
                work_order_id=orden.id,
                crew_id=crew.id,
                scheduled_for=(AHORA - hace).date(),
                assigned_at=AHORA - hace,
                unassigned_at=AHORA - hasta if hasta is not None else None,
            )
        ]
    )


async def _cierre(
    orden: WorkOrder,
    user: User,
    hace: timedelta,
    outcome: ClosureOutcome = ClosureOutcome.done,
    not_done_reason: NotDoneReason | None = None,
) -> None:
    await _seed(
        [
            WorkOrderClosure(
                work_order_id=orden.id,
                closed_by=user.id,
                closed_at=AHORA - hace,
                outcome=outcome,
                not_done_reason=not_done_reason,
                observation="Observación que el celular no vuelve a ver",
                idempotency_key=uuid.uuid4(),
            )
        ]
    )


async def _seed(items: Sequence[object]) -> None:
    async with SessionLocal() as session:
        session.add_all(list(items))
        await session.commit()


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


async def _get(user: User) -> Response:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(URL, headers=_auth(user))


def _numeros(response: Response) -> list[int]:
    return [o["number"] for o in response.json()["orders"]]


# Criterios 1 y 3: los cierres de mi escuadrilla, con cualquier resultado, el más reciente primero.
async def test_ve_sus_cierres_de_la_semana_del_mas_reciente_al_mas_viejo(
    celular: User, escuadrilla: Crew, sede: ClientSite, reparacion: WorkType
) -> None:
    resuelta = await _orden(sede, reparacion)
    otra_visita = await _orden(sede, reparacion, OrderStatus.pending)
    no_se_pudo = await _orden(sede, reparacion, OrderStatus.pending)
    for orden in (resuelta, otra_visita, no_se_pudo):
        await _asignar(orden, escuadrilla, timedelta(days=10))
    await _cierre(
        no_se_pudo, celular, timedelta(days=6), ClosureOutcome.not_done, NotDoneReason.client_absent
    )
    await _cierre(resuelta, celular, timedelta(hours=2))
    await _cierre(otra_visita, celular, timedelta(days=1), ClosureOutcome.needs_revisit)

    response = await _get(celular)

    assert response.status_code == 200
    assert response.json()["crew"] == {"name": "Escuadrilla 1"}
    assert _numeros(response) == [resuelta.number, otra_visita.number, no_se_pudo.number]
    assert [(o["outcome"], o["not_done_reason"]) for o in response.json()["orders"]] == [
        ("done", None),
        ("needs_revisit", None),
        ("not_done", "client_absent"),
    ]


# Criterio 2: lo que muestra la tarjeta.
async def test_cada_cierre_trae_lo_de_la_tarjeta(
    celular: User, escuadrilla: Crew, sede: ClientSite, reparacion: WorkType
) -> None:
    orden = await _orden(sede, reparacion)
    await _asignar(orden, escuadrilla, timedelta(days=2))
    await _cierre(orden, celular, timedelta(days=1))

    (item,) = (await _get(celular)).json()["orders"]

    assert item == {
        "id": str(orden.id),
        "number": orden.number,
        "work_type_name": "Reparación",
        "description": "Cámara no enfría",
        "client_name": "Sanatorio Ficticio",
        "address": "Calle 1",
        "outcome": "done",
        "not_done_reason": None,
        "closed_at": item["closed_at"],
    }
    cerrada = datetime.fromisoformat(item["closed_at"])
    assert abs(cerrada - (AHORA - timedelta(days=1))) < timedelta(seconds=1)


# Criterio 3: cuenta el cierre aunque después la orden se cancele o se reasigne.
async def test_cuenta_el_cierre_aunque_la_orden_haya_cambiado_despues(
    celular: User,
    escuadrilla: Crew,
    otra_escuadrilla: Crew,
    sede: ClientSite,
    reparacion: WorkType,
) -> None:
    cancelada = await _orden(sede, reparacion, OrderStatus.cancelled)
    reasignada = await _orden(sede, reparacion, OrderStatus.assigned)
    await _asignar(cancelada, escuadrilla, timedelta(days=5))
    await _cierre(cancelada, celular, timedelta(days=4), ClosureOutcome.needs_revisit)
    await _asignar(reasignada, escuadrilla, timedelta(days=5), hasta=timedelta(days=4))
    await _cierre(reasignada, celular, timedelta(days=4), ClosureOutcome.needs_revisit)
    await _asignar(reasignada, otra_escuadrilla, timedelta(days=3))

    assert sorted(_numeros(await _get(celular))) == sorted([cancelada.number, reasignada.number])


# Una orden cerrada dos veces por la escuadrilla aparece una vez por cierre.
async def test_una_fila_por_cierre(
    celular: User, escuadrilla: Crew, sede: ClientSite, reparacion: WorkType
) -> None:
    orden = await _orden(sede, reparacion)
    await _asignar(orden, escuadrilla, timedelta(days=5), hasta=timedelta(days=4))
    await _cierre(orden, celular, timedelta(days=4), ClosureOutcome.needs_revisit)
    await _asignar(orden, escuadrilla, timedelta(days=3))
    await _cierre(orden, celular, timedelta(days=2))

    response = await _get(celular)

    assert _numeros(response) == [orden.number, orden.number]
    assert [o["outcome"] for o in response.json()["orders"]] == ["done", "needs_revisit"]


# Criterio 4: ni cierres de otra escuadrilla ni de hace más de 7 días.
async def test_no_ve_cierres_ajenos_ni_viejos(
    celular: User,
    escuadrilla: Crew,
    otra_escuadrilla: Crew,
    sede: ClientSite,
    reparacion: WorkType,
) -> None:
    ajena = await _orden(sede, reparacion)
    await _asignar(ajena, otra_escuadrilla, timedelta(days=2))
    await _cierre(ajena, celular, timedelta(days=1))
    vieja = await _orden(sede, reparacion)
    await _asignar(vieja, escuadrilla, timedelta(days=9))
    await _cierre(vieja, celular, timedelta(days=7, minutes=1))
    reciente = await _orden(sede, reparacion)
    await _asignar(reciente, escuadrilla, timedelta(days=9))
    await _cierre(reciente, celular, timedelta(days=6, hours=23))

    assert _numeros(await _get(celular)) == [reciente.number]


# Criterio 5: sin quién pidió, contactos, observación ni nada del cierre más allá del resultado.
async def test_no_expone_datos_que_el_tecnico_no_ve(
    celular: User, escuadrilla: Crew, sede: ClientSite, reparacion: WorkType
) -> None:
    orden = await _orden(sede, reparacion)
    await _asignar(orden, escuadrilla, timedelta(days=2))
    await _cierre(orden, celular, timedelta(days=1))

    response = await _get(celular)

    claves = _claves(response.json())
    assert not claves & {
        "requester_name",
        "phone",
        "email",
        "price",
        "history",
        "observation",
        "photos",
        "signature",
    }
    for texto in ("Encargado Ficticio", "3850000000", "marta@ficticio.com", "Observación"):
        assert texto not in response.text


def _claves(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {k for v in value.values() for k in _claves(v)}
    if isinstance(value, list):
        return {k for v in value for k in _claves(v)}
    return set()


# Criterio 6: sin cierres en la semana, o sin escuadrilla activa.
async def test_escuadrilla_sin_cierres_recibe_lista_vacia(celular: User, escuadrilla: Crew) -> None:
    body = (await _get(celular)).json()
    assert body == {"crew": {"name": "Escuadrilla 1"}, "orders": []}


async def test_usuario_sin_escuadrilla_no_ve_cierres(celular: User) -> None:
    response = await _get(celular)
    assert response.status_code == 200
    assert response.json() == {"crew": None, "orders": []}


@pytest.mark.parametrize("role", [UserRole.admin, UserRole.owner])
async def test_otros_roles_reciben_403(schema: None, role: UserRole) -> None:
    user = make_user(email=f"{role.value}@ot-demo.com", role=role)
    await _seed([user])
    assert (await _get(user)).status_code == 403


async def test_sin_sesion_recibe_401(schema: None) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get(URL)).status_code == 401
