"""E04-14: importes y estado de cobro de una orden terminada (versión mínima)."""

import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import text

from app.db.models.catalog import WorkType
from app.db.models.client import Client, ClientSite
from app.db.models.crew import Crew
from app.db.models.user import User, UserRole
from app.db.session import engine
from app.domain.work_order import OrderStatus
from app.main import app
from tests.factories import make_user
from tests.test_work_order_closure_admin import (
    ORDERS_URL,
    TABLES,
    Mundo,
    _auth,
    _cierre,
    _get,
    _orden,
    _seed,
)


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
            "cancel_reason",
            "no_signature_reason",
            "signature_purpose",
            "billing_status",
        ):
            await conn.execute(text(f"DROP TYPE IF EXISTS {enum_type}"))
        await conn.execute(text("DROP SEQUENCE IF EXISTS work_order_number_seq"))


@pytest.fixture
async def mundo(schema: None) -> Mundo:
    admin = make_user(email="admin@ot-demo.com", role=UserRole.admin, full_name="Admin Ficticia")
    celular = make_user(email="esc1@ot-demo.com", role=UserRole.technician, full_name="Celular 1")
    await _seed([admin, celular])
    escuadrilla = Crew(name="Escuadrilla 1", app_user_id=celular.id)
    cliente = Client(id=uuid.uuid4(), number="10642", name="Sanatorio Ficticio")
    reparacion = WorkType(name="Reparación")
    await _seed([escuadrilla, cliente, reparacion])
    sede = ClientSite(client_id=cliente.id, label="Central", address="Calle 1")
    await _seed([sede])
    return Mundo(
        admin=admin, celular=celular, escuadrilla=escuadrilla, sede=sede, reparacion=reparacion
    )


async def _put(user: User, order_id: uuid.UUID, body: dict[str, Any]) -> Response:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.put(f"{ORDERS_URL}/{order_id}/billing", json=body, headers=_auth(user))


async def _terminada(m: Mundo) -> Any:
    orden = await _orden(m, OrderStatus.done)
    await _cierre(m, orden)
    return orden


# Como lo manda la administración: sin factura, el número va en null.
IMPORTES = {
    "parts_amount": "15000.50",
    "labor_amount": "20000",
    "status": "pending",
    "invoice_number": None,
}


# Criterio 1: guarda repuestos y mano de obra, con quién y cuándo, y el total.
async def test_carga_importes_de_una_terminada(mundo: Mundo) -> None:
    m = mundo
    orden = await _terminada(m)

    response = await _put(m.admin, orden.id, IMPORTES)

    assert response.status_code == 200
    body = response.json()
    assert body["parts_amount"] == "15000.50"
    assert body["labor_amount"] == "20000.00"
    assert body["total"] == "35000.50"
    assert body["status"] == "pending"
    assert body["invoice_number"] is None
    assert body["updated_by_name"] == "Admin Ficticia"


# Criterio 2: se marca facturada con número y se puede volver atrás; reemplaza lo anterior.
async def test_marca_facturada_y_reemplaza(mundo: Mundo) -> None:
    m = mundo
    orden = await _terminada(m)
    await _put(m.admin, orden.id, IMPORTES)

    facturada = await _put(
        m.admin, orden.id, {**IMPORTES, "status": "invoiced", "invoice_number": " A-0001-123 "}
    )
    de_vuelta = await _put(m.admin, orden.id, {**IMPORTES, "labor_amount": "1"})

    assert facturada.json()["status"] == "invoiced"
    assert facturada.json()["invoice_number"] == "A-0001-123"
    assert de_vuelta.json()["status"] == "pending"
    assert de_vuelta.json()["total"] == "15001.50"


# Criterio 3: el listado trae el cobro y filtra; sin datos cargados está pendiente.
async def test_listado_muestra_y_filtra_por_estado_de_cobro(mundo: Mundo) -> None:
    m = mundo
    sin_datos = await _terminada(m)
    pendiente = await _terminada(m)
    facturada = await _terminada(m)
    await _put(m.admin, pendiente.id, IMPORTES)
    await _put(m.admin, facturada.id, {**IMPORTES, "status": "invoiced"})

    todas = (await _get(m.admin, f"{ORDERS_URL}?status=done")).json()
    pendientes = (await _get(m.admin, f"{ORDERS_URL}?status=done&billing=pending")).json()
    facturadas = (await _get(m.admin, f"{ORDERS_URL}?status=done&billing=invoiced")).json()

    por_numero = {item["number"]: item["billing"] for item in todas["items"]}
    assert por_numero[sin_datos.number] is None
    assert por_numero[pendiente.number]["total"] == "35000.50"
    assert {i["number"] for i in pendientes["items"]} == {sin_datos.number, pendiente.number}
    assert pendientes["total"] == 2
    assert [i["number"] for i in facturadas["items"]] == [facturada.number]


# Criterio 4: solo terminadas.
@pytest.mark.parametrize("status", [OrderStatus.pending, OrderStatus.in_progress])
async def test_rechaza_una_orden_no_terminada(mundo: Mundo, status: OrderStatus) -> None:
    orden = await _orden(mundo, status)

    response = await _put(mundo.admin, orden.id, IMPORTES)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "order_not_done"


async def test_orden_inexistente_da_404(mundo: Mundo) -> None:
    response = await _put(mundo.admin, uuid.uuid4(), IMPORTES)

    assert response.status_code == 404


# Criterio 5: importes válidos.
@pytest.mark.parametrize(("campo", "valor"), [("parts_amount", "-1"), ("labor_amount", "10.123")])
async def test_rechaza_importes_invalidos(mundo: Mundo, campo: str, valor: str) -> None:
    orden = await _terminada(mundo)

    response = await _put(mundo.admin, orden.id, {**IMPORTES, campo: valor})

    assert response.status_code == 422
    assert campo in str(response.json())


# Criterio 6: solo administración.
@pytest.mark.parametrize("role", [UserRole.technician, UserRole.owner])
async def test_tecnico_y_direccion_reciben_403(mundo: Mundo, role: UserRole) -> None:
    orden = await _terminada(mundo)
    otro = make_user(email=f"{role.value}@ot-demo.com", role=role)
    await _seed([otro])

    response = await _put(otro, orden.id, IMPORTES)

    assert response.status_code == 403
