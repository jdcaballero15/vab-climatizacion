"""E04-14: importes y estado de cobro de una orden terminada (versión mínima)."""

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import text

from app.db.models.catalog import WorkType
from app.db.models.client import Client, ClientSite
from app.db.models.crew import Crew
from app.db.models.part import Part, PartPrice, PartUsage
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
            "payment_method",
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


async def _terminada(m: Mundo, materiales: str | None = "15000.50") -> Any:
    """Terminada con un material usado que, al precio de lista, suma ese importe."""
    orden = await _orden(m, OrderStatus.done)
    await _cierre(m, orden)
    if materiales is not None:
        part = Part(name=f"Material {uuid.uuid4().hex[:6]}", unit="unidad")
        await _seed([part])
        await _seed(
            [
                PartPrice(part_id=part.id, list_price=Decimal(materiales)),
                PartUsage(
                    work_order_id=orden.id,
                    part_id=part.id,
                    quantity=Decimal("1"),
                    created_by=m.celular.id,
                ),
            ]
        )
    return orden


async def _aprobar(m: Mundo, order_id: uuid.UUID) -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(f"{ORDERS_URL}/{order_id}/approval", headers=_auth(m.admin))
    assert response.status_code == 200, response.text


IMPORTES = {"labor_amount": "20000"}
HOY = "2026-11-10"


async def _post(user: User, url: str, body: dict[str, Any]) -> Response:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.post(url, json=body, headers=_auth(user))


async def _send(user: User, method: str, url: str, body: dict[str, Any] | None = None) -> Response:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.request(method, url, json=body, headers=_auth(user))


async def _facturar(m: Mundo, *ordenes: Any, numero: str = "A-0001-00000123") -> Response:
    return await _post(
        m.admin,
        "/admin/invoices",
        {"number": numero, "issued_on": HOY, "order_ids": [str(o.id) for o in ordenes]},
    )


async def _facturada(m: Mundo) -> Any:
    orden = await _terminada(m)
    await _aprobar(m, orden.id)
    assert (await _facturar(m, orden)).status_code == 201
    return orden


async def _estado(m: Mundo, orden: Any) -> str:
    return str((await _get(m.admin, f"{ORDERS_URL}/{orden.id}")).json()["status"])


async def _timeline(m: Mundo, orden: Any) -> list[tuple[str, str | None]]:
    body = (await _get(m.admin, f"{ORDERS_URL}/{orden.id}")).json()
    return [(e["event_type"], e["note"]) for e in body["timeline"]]


# E04-14: la mano de obra se carga a mano; repuestos y total se calculan.
async def test_carga_la_mano_de_obra_de_una_terminada(mundo: Mundo) -> None:
    m = mundo
    orden = await _terminada(m)

    response = await _put(m.admin, orden.id, IMPORTES)

    assert response.status_code == 200
    body = response.json()
    assert body["parts_amount"] == "15000.50"
    assert body["labor_amount"] == "20000.00"
    assert body["charges_amount"] == "0.00"
    assert body["total"] == "35000.50"
    assert body["invoice"] is None
    assert body["payment"] is None
    assert body["updated_by_name"] == "Admin Ficticia"


# E05-05: los repuestos ya no se cargan a mano; el estado de cobro tampoco va acá.
@pytest.mark.parametrize("extra", [{"parts_amount": "1"}, {"status": "invoiced"}])
async def test_campos_que_no_van_se_rechazan(mundo: Mundo, extra: dict[str, str]) -> None:
    orden = await _terminada(mundo)

    response = await _put(mundo.admin, orden.id, {**IMPORTES, **extra})

    assert response.status_code == 422


# E04-11, criterios 1, 2 y 4: otros cargos con descripción e importe, en el total y en la
# línea de tiempo al agregarlos, corregirlos o sacarlos.
async def test_otros_cargos_suman_al_total_y_quedan_en_la_linea_de_tiempo(mundo: Mundo) -> None:
    m = mundo
    orden = await _terminada(m)
    url = f"{ORDERS_URL}/{orden.id}/charges"
    await _put(m.admin, orden.id, IMPORTES)

    alta = await _post(m.admin, url, {"description": " Visita fuera de horario ", "amount": "5000"})
    cargo = alta.json()[0]
    corregido = await _send(
        m.admin, "PUT", f"{url}/{cargo['id']}", {"description": "Visita nocturna", "amount": "6000"}
    )
    await _post(m.admin, url, {"description": "Viáticos", "amount": "1000"})
    billing = (await _get(m.admin, f"{ORDERS_URL}/{orden.id}/billing")).json()
    sacado = await _send(m.admin, "DELETE", f"{url}/{cargo['id']}")

    assert alta.status_code == 201
    assert cargo["description"] == "Visita fuera de horario"
    assert cargo["created_by_name"] == "Admin Ficticia"
    assert corregido.json()[0]["amount"] == "6000.00"
    assert billing["charges_amount"] == "7000.00"
    assert billing["total"] == "42000.50"
    assert [c["description"] for c in sacado.json()] == ["Viáticos"]
    notas = [nota for tipo, nota in await _timeline(m, orden) if tipo == "charges_changed"]
    assert notas == [
        "Cargo agregado: Visita fuera de horario, $ 5.000,00",
        "Cargo corregido: Visita fuera de horario, $ 5.000,00 pasó a Visita nocturna, $ 6.000,00",
        "Cargo agregado: Viáticos, $ 1.000,00",
        "Cargo sacado: Visita nocturna, $ 6.000,00",
    ]


async def test_cargo_sin_descripcion_o_negativo_se_rechaza(mundo: Mundo) -> None:
    orden = await _terminada(mundo)
    url = f"{ORDERS_URL}/{orden.id}/charges"

    vacio = await _post(mundo.admin, url, {"description": " ", "amount": "1"})
    negativo = await _post(mundo.admin, url, {"description": "Visita", "amount": "-1"})

    assert vacio.status_code == 422
    assert negativo.status_code == 422


# E04-09, criterio 1: una factura pasa la orden a Facturada con usuario y fecha. Una misma
# factura cubre varias órdenes (Gonza, 2026-11-10).
async def test_una_factura_para_varias_ordenes(mundo: Mundo) -> None:
    m = mundo
    primera = await _terminada(m)
    segunda = await _terminada(m)
    for orden in (primera, segunda):
        await _aprobar(m, orden.id)

    response = await _facturar(m, primera, segunda)

    assert response.status_code == 201
    factura = response.json()
    assert factura["number"] == "A-0001-00000123"
    assert factura["order_numbers"] == sorted([primera.number, segunda.number])
    assert await _estado(m, primera) == "invoiced"
    assert await _estado(m, segunda) == "invoiced"
    billing = (await _get(m.admin, f"{ORDERS_URL}/{primera.id}/billing")).json()
    assert billing["invoice"]["number"] == "A-0001-00000123"
    assert ("status_change", "Factura A-0001-00000123 del 10/11/2026") in await _timeline(
        m, primera
    )


# Criterio 2 y E04-08: sin aprobar, o sin terminar, no se factura ninguna.
async def test_si_una_no_se_puede_no_se_factura_ninguna(mundo: Mundo) -> None:
    m = mundo
    aprobada = await _terminada(m)
    await _aprobar(m, aprobada.id)
    sin_aprobar = await _terminada(m)
    en_curso = await _orden(m, OrderStatus.in_progress)

    falta_aprobar = await _facturar(m, aprobada, sin_aprobar)
    no_terminada = await _facturar(m, aprobada, en_curso)

    assert falta_aprobar.status_code == 409
    assert f"N° {sin_aprobar.number}" in falta_aprobar.json()["detail"]["message"]
    assert no_terminada.status_code == 409
    assert no_terminada.json()["detail"]["code"] == "orders_not_invoiceable"
    assert await _estado(m, aprobada) == "done"


# Criterio 3: sin número, no.
async def test_factura_sin_numero_se_rechaza(mundo: Mundo) -> None:
    m = mundo
    orden = await _terminada(m)
    await _aprobar(m, orden.id)

    response = await _facturar(m, orden, numero="  ")

    assert response.status_code == 422


# Criterio 4: corregir el número queda en la línea de tiempo de cada orden.
async def test_corregir_la_factura_queda_auditado(mundo: Mundo) -> None:
    m = mundo
    orden = await _terminada(m)
    await _aprobar(m, orden.id)
    factura = (await _facturar(m, orden)).json()

    response = await _send(
        m.admin,
        "PUT",
        f"/admin/invoices/{factura['id']}",
        {"number": "A-0001-00000124", "issued_on": "2026-11-11"},
    )

    assert response.status_code == 200
    assert response.json()["number"] == "A-0001-00000124"
    assert (
        "invoice_corrected",
        "Factura corregida: A-0001-00000123 del 10/11/2026 pasó a A-0001-00000124 del 11/11/2026",
    ) in await _timeline(m, orden)


# Facturada, los importes ya no se tocan.
async def test_facturada_no_cambia_importes(mundo: Mundo) -> None:
    m = mundo
    orden = await _facturada(m)

    mano_de_obra = await _put(m.admin, orden.id, IMPORTES)
    cargo = await _post(
        m.admin, f"{ORDERS_URL}/{orden.id}/charges", {"description": "Visita", "amount": "1"}
    )

    assert mano_de_obra.status_code == 409
    assert cargo.status_code == 409


# E04-10, criterio 1: el cobro, con fecha y medio, la pasa a Cobrada.
async def test_registra_el_cobro(mundo: Mundo) -> None:
    m = mundo
    orden = await _facturada(m)

    response = await _post(
        m.admin, f"{ORDERS_URL}/{orden.id}/payment", {"paid_on": HOY, "method": "transfer"}
    )

    assert response.status_code == 200
    pago = response.json()["payment"]
    assert pago["paid_on"] == HOY
    assert pago["method"] == "transfer"
    assert pago["created_by_name"] == "Admin Ficticia"
    assert await _estado(m, orden) == "paid"
    assert ("status_change", "Cobrada el 10/11/2026 (Transferencia)") in await _timeline(m, orden)


# Criterio 2: solo una Facturada se cobra.
async def test_no_se_cobra_una_no_facturada(mundo: Mundo) -> None:
    m = mundo
    orden = await _terminada(m)

    response = await _post(
        m.admin, f"{ORDERS_URL}/{orden.id}/payment", {"paid_on": HOY, "method": "cash"}
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "order_not_invoiced"


# Criterio 4: anular el cobro la vuelve a Facturada, con motivo; se puede cobrar de nuevo.
async def test_anular_el_cobro(mundo: Mundo) -> None:
    m = mundo
    orden = await _facturada(m)
    url = f"{ORDERS_URL}/{orden.id}/payment"
    await _post(m.admin, url, {"paid_on": HOY, "method": "cash"})

    sin_motivo = await _post(m.admin, f"{url}/void", {"reason": " "})
    anulado = await _post(m.admin, f"{url}/void", {"reason": "Se cargó en la orden equivocada."})
    otra_vez = await _post(m.admin, url, {"paid_on": HOY, "method": "check"})

    assert sin_motivo.status_code == 422
    assert anulado.status_code == 200
    assert anulado.json()["payment"] is None
    assert otra_vez.json()["payment"]["method"] == "check"
    assert (
        "status_change",
        "Cobro anulado. Motivo: Se cargó en la orden equivocada.",
    ) in await _timeline(m, orden)


# E04-05: las facturadas y cobradas se listan con su factura y su cobro.
async def test_listado_de_facturadas_y_cobradas(mundo: Mundo) -> None:
    m = mundo
    facturada = await _facturada(m)
    cobrada = await _facturada(m)
    await _post(m.admin, f"{ORDERS_URL}/{cobrada.id}/payment", {"paid_on": HOY, "method": "cash"})

    facturadas = (await _get(m.admin, f"{ORDERS_URL}?status=invoiced")).json()
    cobradas = (await _get(m.admin, f"{ORDERS_URL}?status=paid")).json()

    assert [i["number"] for i in facturadas["items"]] == [facturada.number]
    assert facturadas["items"][0]["billing"]["invoice"]["number"] == "A-0001-00000123"
    assert facturadas["items"][0]["completed"] is not None
    assert [i["number"] for i in cobradas["items"]] == [cobrada.number]
    assert cobradas["items"][0]["billing"]["payment"]["method"] == "cash"


@pytest.mark.parametrize("status", [OrderStatus.pending, OrderStatus.in_progress])
async def test_rechaza_una_orden_no_terminada(mundo: Mundo, status: OrderStatus) -> None:
    orden = await _orden(mundo, status)

    response = await _put(mundo.admin, orden.id, IMPORTES)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "order_not_done"


async def test_orden_inexistente_da_404(mundo: Mundo) -> None:
    response = await _put(mundo.admin, uuid.uuid4(), IMPORTES)

    assert response.status_code == 404


@pytest.mark.parametrize("valor", ["-1", "10.123"])
async def test_rechaza_importes_invalidos(mundo: Mundo, valor: str) -> None:
    orden = await _terminada(mundo)

    response = await _put(mundo.admin, orden.id, {"labor_amount": valor})

    assert response.status_code == 422
    assert "labor_amount" in str(response.json())


# Solo administración carga importes, factura y cobra; dirección los ve.
@pytest.mark.parametrize("role", [UserRole.technician, UserRole.owner])
async def test_tecnico_y_direccion_no_cargan_nada(mundo: Mundo, role: UserRole) -> None:
    m = mundo
    orden = await _terminada(m)
    otro = make_user(email=f"{role.value}@ot-demo.com", role=role)
    await _seed([otro])

    importes = await _put(otro, orden.id, IMPORTES)
    cargo = await _post(
        otro, f"{ORDERS_URL}/{orden.id}/charges", {"description": "Visita", "amount": "1"}
    )
    factura = await _post(
        otro, "/admin/invoices", {"number": "A-1", "issued_on": HOY, "order_ids": [str(orden.id)]}
    )
    cobro = await _post(
        otro, f"{ORDERS_URL}/{orden.id}/payment", {"paid_on": HOY, "method": "cash"}
    )

    assert {importes.status_code, cargo.status_code, factura.status_code, cobro.status_code} == {
        403
    }


async def test_direccion_ve_importes_y_el_panel(mundo: Mundo) -> None:
    m = mundo
    orden = await _terminada(m)
    direccion = make_user(email="direccion@ot-demo.com", role=UserRole.owner)
    await _seed([direccion])

    billing = await _get(direccion, f"{ORDERS_URL}/{orden.id}/billing")
    panel = await _get(direccion, f"{ORDERS_URL}?status=done")

    assert billing.status_code == 200
    assert panel.status_code == 200


async def test_tecnico_no_ve_el_panel_ni_importes(mundo: Mundo) -> None:
    m = mundo
    orden = await _terminada(m)

    billing = await _get(m.celular, f"{ORDERS_URL}/{orden.id}/billing")
    panel = await _get(m.celular, f"{ORDERS_URL}?status=done")

    assert billing.status_code == 403
    assert panel.status_code == 403


# E04-05, criterio 4: una terminada hace más de 7 días sin facturar se destaca.
async def test_terminada_sin_facturar_hace_mas_de_una_semana_se_destaca(mundo: Mundo) -> None:
    m = mundo
    reciente = await _orden(m, OrderStatus.done)
    await _cierre(m, reciente)
    vieja = await _orden(m, OrderStatus.done)
    await _cierre(m, vieja, closed_at=datetime.now(UTC) - timedelta(days=8))

    body = (await _get(m.admin, f"{ORDERS_URL}?status=done")).json()

    demora = {item["number"]: item["billing_overdue"] for item in body["items"]}
    assert demora == {reciente.number: False, vieja.number: True}


# E04-05, criterio 2: filtros por escuadrilla, cliente, tipo de trabajo y período.
async def test_filtros_del_panel(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m, OrderStatus.assigned)
    otro_cliente = Client(id=uuid.uuid4(), number="20001", name="Hotel Ficticio")
    service = WorkType(name="Service")
    await _seed([otro_cliente, service])
    hoy = datetime.now(UTC).date()
    base = f"{ORDERS_URL}?status=assigned"

    async def numeros(query: str) -> list[int]:
        body = (await _get(m.admin, f"{base}&{query}")).json()
        return [item["number"] for item in body["items"]]

    assert await numeros(f"crew_id={m.escuadrilla.id}") == [orden.number]
    assert await numeros(f"crew_id={uuid.uuid4()}") == []
    assert await numeros(f"client_id={orden.client_id}") == [orden.number]
    assert await numeros(f"client_id={otro_cliente.id}") == []
    assert await numeros(f"work_type_id={service.id}") == []
    assert await numeros(f"created_from={hoy - timedelta(days=1)}&created_to={hoy}") == [
        orden.number
    ]
    assert await numeros(f"created_from={hoy + timedelta(days=1)}") == []


def _reparacion(m: Mundo, origen: Any, **extra: Any) -> dict[str, Any]:
    return {
        "client_id": str(m.sede.client_id),
        "client_site_id": str(m.sede.id),
        "work_type_id": str(m.reparacion.id),
        "channel": "phone",
        "description": "Pierde agua el drenaje (observación del cierre).",
        "source_order_id": str(origen.id),
        **extra,
    }


# E04-13: la orden de reparación nace de una cerrada y las dos muestran la relación.
async def test_orden_de_reparacion_desde_un_cierre(mundo: Mundo) -> None:
    m = mundo
    origen = await _terminada(m)

    response = await _post(m.admin, ORDERS_URL, _reparacion(m, origen))

    assert response.status_code == 201, response.text
    nueva = response.json()
    detalle_nueva = (await _get(m.admin, f"{ORDERS_URL}/{nueva['id']}")).json()
    detalle_origen = (await _get(m.admin, f"{ORDERS_URL}/{origen.id}")).json()
    assert detalle_nueva["source_order"]["number"] == origen.number
    assert [o["number"] for o in detalle_origen["repair_orders"]] == [nueva["number"]]
    assert (
        "repair_order_opened",
        f"Se abrió la orden N° {nueva['number']}",
    ) in await _timeline(m, origen)


async def test_orden_de_reparacion_exige_origen_cerrado_y_del_mismo_cliente(mundo: Mundo) -> None:
    m = mundo
    abierta = await _orden(m, OrderStatus.assigned)
    cerrada = await _terminada(m)
    otro = Client(id=uuid.uuid4(), number="20002", name="Hotel Ficticio")
    await _seed([otro])
    otra_sede = ClientSite(client_id=otro.id, label="Única", address="Calle 2")
    await _seed([otra_sede])

    no_cerrada = await _post(m.admin, ORDERS_URL, _reparacion(m, abierta))
    de_otro = await _post(
        m.admin,
        ORDERS_URL,
        _reparacion(m, cerrada, client_id=str(otro.id), client_site_id=str(otra_sede.id)),
    )

    assert no_cerrada.status_code == 422
    assert no_cerrada.json()["detail"]["code"] == "source_order_not_closed"
    assert de_otro.status_code == 422
    assert de_otro.json()["detail"]["code"] == "source_order_of_another_client"
