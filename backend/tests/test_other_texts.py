"""E02-07: los textos de "Otro" más repetidos se suman a la lista o se descartan."""

import uuid
from collections.abc import AsyncGenerator
from decimal import Decimal
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select, text

from app.db.models.catalog import Failure
from app.db.models.other_text import DismissedOtherText
from app.db.models.part import Part, PartUsage
from app.db.models.user import User
from app.db.models.work_order import WorkOrderClosure
from app.db.session import SessionLocal, engine
from app.domain.work_order import ClosureOutcome, OrderStatus
from app.main import app
from tests import test_work_order_closure_admin as cierre
from tests.test_work_order_closure_admin import TABLES, Mundo, _auth, _orden, _seed

mundo = cierre.mundo
OTHER_TABLES = [*TABLES, DismissedOtherText.__table__]
ENUMS = (
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
    "cancel_reason",
    "no_signature_reason",
    "signature_purpose",
    "billing_status",
    "workshop_stage",
    "check_result",
)


@pytest.fixture
async def schema() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.create_all, tables=OTHER_TABLES)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.drop_all, tables=list(reversed(OTHER_TABLES)))
        for enum_type in ENUMS:
            await conn.execute(text(f"DROP TYPE IF EXISTS {enum_type}"))
        await conn.execute(text("DROP SEQUENCE IF EXISTS work_order_number_seq"))


async def _call(user: Any, method: str, url: str, body: dict[str, Any] | None = None) -> Response:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.request(method, url, json=body, headers=_auth(user))


async def _cierre_con_falla(m: Mundo, falla: str) -> WorkOrderClosure:
    orden = await _orden(m, OrderStatus.done)
    closure = WorkOrderClosure(
        work_order_id=orden.id,
        closed_by=m.celular.id,
        idempotency_key=uuid.uuid4(),
        outcome=ClosureOutcome.done,
        failure_other_text=falla,
    )
    await _seed([closure])
    return closure


# Criterio 1: cada texto con sus repeticiones, agrupando mayúsculas y espacios.
async def test_agrupa_variantes_y_cuenta(mundo: Mundo) -> None:
    m = mundo
    for falla in ("Burlete roto", "burlete  roto", "BURLETE ROTO", "Ruido raro"):
        await _cierre_con_falla(m, falla)

    response = await _call(m.admin, "GET", "/admin/other-texts?kind=failure")

    assert response.json() == [
        {"text_key": "burlete roto", "text": "Burlete roto", "count": 3},
        {"text_key": "ruido raro", "text": "Ruido raro", "count": 1},
    ]


# Criterio 2: al promoverlo se crea en la lista y las órdenes pasan a referenciarlo.
async def test_promover_crea_la_falla_y_actualiza_las_ordenes(mundo: Mundo) -> None:
    m = mundo
    cierres = [await _cierre_con_falla(m, f) for f in ("Burlete roto", "burlete roto")]

    response = await _call(
        m.admin,
        "POST",
        "/admin/other-texts/promote",
        {"kind": "failure", "text_key": "burlete roto", "name": "Burlete roto"},
    )
    pendientes = (await _call(m.admin, "GET", "/admin/other-texts?kind=failure")).json()

    assert response.json() == {"updated": 2}
    assert pendientes == []
    async with SessionLocal() as session:
        falla = await session.scalar(select(Failure).where(Failure.name == "Burlete roto"))
        assert falla is not None
        for original in cierres:
            guardado = await session.get(WorkOrderClosure, original.id)
            assert guardado is not None
            assert (guardado.failure_id, guardado.failure_other_text) == (falla.id, None)


# Un material escrito a mano puede ir a uno que ya está en la lista.
async def test_promover_un_material_a_uno_existente(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m, OrderStatus.done)
    cinta = Part(name="Cinta aisladora", unit="unidad")
    await _seed([cinta])
    uso = PartUsage(
        work_order_id=orden.id,
        other_text="cinta aisladora ",
        quantity=Decimal("1"),
        created_by=m.celular.id,
    )
    await _seed([uso])

    response = await _call(
        m.admin,
        "POST",
        "/admin/other-texts/promote",
        {"kind": "part", "text_key": "cinta aisladora", "target_id": str(cinta.id)},
    )

    assert response.json() == {"updated": 1}
    async with SessionLocal() as session:
        guardado = await session.get(PartUsage, uso.id)
        assert guardado is not None and guardado.part_id == cinta.id


# Criterio 3: descartado no se muestra, pero la orden lo conserva.
async def test_descartar(mundo: Mundo) -> None:
    m = mundo
    closure = await _cierre_con_falla(m, "Ruido raro")

    response = await _call(
        m.admin, "POST", "/admin/other-texts/dismiss", {"kind": "failure", "text_key": "ruido raro"}
    )
    pendientes = (await _call(m.admin, "GET", "/admin/other-texts?kind=failure")).json()

    assert response.status_code == 204
    assert pendientes == []
    async with SessionLocal() as session:
        guardado = await session.get(WorkOrderClosure, closure.id)
        assert guardado is not None and guardado.failure_other_text == "Ruido raro"


async def test_solo_administracion(mundo: Mundo) -> None:
    response = await _call(mundo.celular, "GET", "/admin/other-texts?kind=failure")
    assert response.status_code == 403
