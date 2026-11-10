"""E08: stock por movimientos. Depósitos y camionetas, ingresos, transferencias, ajustes,
el descuento al cerrar desde la camioneta de la escuadrilla y las consultas."""

import uuid
from decimal import Decimal
from typing import Any

import pytest
from httpx import Response
from sqlalchemy import func, select

from app.db.models.part import Part
from app.db.models.stock import StockMovement
from app.db.models.user import User, UserRole
from app.db.session import SessionLocal
from tests import test_tech_order_closure as cierre
from tests.factories import make_user
from tests.test_tech_order_closure import (
    Mundo,
    _auth,
    _cerrar,
    _client,
    _materiales,
    _orden,
    _resuelta,
    _seed,
)

URL = "/admin/stock"
# El mismo mundo ficticio que los tests del cierre: escuadrilla, celular, catálogo y sede.
schema = cierre.schema
mundo = cierre.mundo


async def _admin() -> User:
    admin = make_user(email="admin@ot-demo.com", role=UserRole.admin, full_name="Admin Ficticia")
    await _seed([admin])
    return admin


async def _call(user: User, method: str, url: str, body: dict[str, Any] | None = None) -> Response:
    async with _client() as client:
        return await client.request(method, url, json=body, headers=_auth(user))


async def _ubicacion(admin: User, nombre: str, **extra: Any) -> dict[str, Any]:
    body = {"kind": "warehouse", "name": nombre, **extra}
    response = await _call(admin, "POST", f"{URL}/locations", body)
    assert response.status_code == 201, response.text
    data: dict[str, Any] = response.json()
    return data


async def _ingreso(admin: User, part: Part, location: dict[str, Any], quantity: str) -> Response:
    return await _call(
        admin,
        "POST",
        f"{URL}/receipts",
        {"part_id": str(part.id), "location_id": location["id"], "quantity": quantity},
    )


def _saldos(stock: list[dict[str, Any]]) -> dict[tuple[str, str], str]:
    return {
        (item["part_name"], row["location_name"]): row["quantity"]
        for item in stock
        for row in item["by_location"]
    }


# E08-01: depósitos y camionetas; la camioneta lleva su escuadrilla, una por escuadrilla,
# y una ubicación se desactiva, no se borra.
async def test_depositos_y_camionetas(mundo: Mundo) -> None:
    admin = await _admin()

    deposito = await _ubicacion(admin, "Depósito central")
    camioneta = await _ubicacion(
        admin, "Camioneta 1", kind="truck", crew_id=str(mundo.escuadrilla.id)
    )
    otra = await _call(
        admin,
        "POST",
        f"{URL}/locations",
        {"kind": "truck", "name": "Camioneta 2", "crew_id": str(mundo.escuadrilla.id)},
    )
    deposito_con_escuadrilla = await _call(
        admin,
        "POST",
        f"{URL}/locations",
        {"kind": "warehouse", "name": "X", "crew_id": str(mundo.escuadrilla.id)},
    )
    baja = await _call(admin, "PATCH", f"{URL}/locations/{deposito['id']}", {"is_active": False})
    activas = (await _call(admin, "GET", f"{URL}/locations")).json()

    assert camioneta["crew_name"] == "Escuadrilla 1"
    assert otra.status_code == 409
    assert deposito_con_escuadrilla.status_code == 422
    assert baja.json()["is_active"] is False
    assert [loc["name"] for loc in activas] == ["Camioneta 1"]


# E08-02, E08-03 y E08-05: ingreso, transferencia en una transacción y el stock por
# ubicación, que es la suma de movimientos.
async def test_ingreso_transferencia_y_consulta(mundo: Mundo) -> None:
    admin = await _admin()
    gas, cano, _ = await _materiales(mundo)
    deposito = await _ubicacion(admin, "Depósito central")
    camioneta = await _ubicacion(admin, "Camioneta 1", kind="truck")

    ingreso = await _ingreso(admin, gas, deposito, "10.5")
    await _ingreso(admin, cano, deposito, "30")
    transferencia = await _call(
        admin,
        "POST",
        f"{URL}/transfers",
        {
            "part_id": str(gas.id),
            "from_location_id": deposito["id"],
            "to_location_id": camioneta["id"],
            "quantity": "4",
        },
    )
    stock = (await _call(admin, "GET", URL)).json()
    solo_gas = (await _call(admin, "GET", f"{URL}?part_id={gas.id}")).json()

    assert ingreso.status_code == 201
    assert ingreso.json()["created_by_name"] == "Admin Ficticia"
    assert transferencia.status_code == 201
    assert _saldos(stock) == {
        ("Caño de cobre 1/4", "Depósito central"): "30.000",
        ("Gas R410A", "Camioneta 1"): "4.000",
        ("Gas R410A", "Depósito central"): "6.500",
    }
    assert [p["part_name"] for p in solo_gas] == ["Gas R410A"]
    assert solo_gas[0]["total"] == "10.500"


@pytest.mark.parametrize("cantidad", ["0", "-1", "1.2345"])
async def test_ingreso_con_cantidad_invalida(mundo: Mundo, cantidad: str) -> None:
    admin = await _admin()
    gas, _, _ = await _materiales(mundo)
    deposito = await _ubicacion(admin, "Depósito central")

    response = await _ingreso(admin, gas, deposito, cantidad)

    assert response.status_code == 422


# E08-03, criterios 2 y 3: no más que lo que hay ni al mismo lugar.
async def test_transferencias_invalidas(mundo: Mundo) -> None:
    admin = await _admin()
    gas, _, _ = await _materiales(mundo)
    deposito = await _ubicacion(admin, "Depósito central")
    camioneta = await _ubicacion(admin, "Camioneta 1", kind="truck")
    await _ingreso(admin, gas, deposito, "2")

    def body(origen: dict[str, Any], destino: dict[str, Any], cantidad: str) -> dict[str, Any]:
        return {
            "part_id": str(gas.id),
            "from_location_id": origen["id"],
            "to_location_id": destino["id"],
            "quantity": cantidad,
        }

    de_mas = await _call(admin, "POST", f"{URL}/transfers", body(deposito, camioneta, "3"))
    mismo = await _call(admin, "POST", f"{URL}/transfers", body(deposito, deposito, "1"))

    assert de_mas.status_code == 409
    assert de_mas.json()["detail"]["code"] == "not_enough_stock"
    assert mismo.status_code == 422


# E08-06: ajuste con motivo, que suma o resta; sin motivo o en cero se rechaza.
async def test_ajustes(mundo: Mundo) -> None:
    admin = await _admin()
    gas, _, _ = await _materiales(mundo)
    deposito = await _ubicacion(admin, "Depósito central")
    await _ingreso(admin, gas, deposito, "5")

    def body(cantidad: str, motivo: str | None) -> dict[str, Any]:
        return {
            "part_id": str(gas.id),
            "location_id": deposito["id"],
            "quantity": cantidad,
            "reason": motivo,
        }

    resta = await _call(admin, "POST", f"{URL}/adjustments", body("-1.5", "Inventario del mes"))
    sin_motivo = await _call(admin, "POST", f"{URL}/adjustments", body("1", "  "))
    cero = await _call(admin, "POST", f"{URL}/adjustments", body("0", "Nada"))
    stock = (await _call(admin, "GET", URL)).json()

    assert resta.status_code == 201
    assert resta.json()["reason"] == "Inventario del mes"
    assert resta.json()["from_location_name"] == "Depósito central"
    assert sin_motivo.status_code == 422
    assert cero.status_code == 422
    assert stock[0]["total"] == "3.500"


# E08-04: al cerrar, lo usado sale de la camioneta de la escuadrilla, una sola vez aunque el
# cierre se reenvíe. Los "Otro" no mueven stock. E08-08: sin stock suficiente se cierra igual
# y la camioneta queda en negativo, destacada.
async def test_el_cierre_descuenta_de_la_camioneta(mundo: Mundo) -> None:
    admin = await _admin()
    gas, cano, _ = await _materiales(mundo)
    camioneta = await _ubicacion(
        admin, "Camioneta 1", kind="truck", crew_id=str(mundo.escuadrilla.id)
    )
    await _ingreso(admin, gas, camioneta, "1")
    orden = await _orden(mundo)
    cierre = _resuelta(
        mundo,
        parts=[
            {"part_id": str(gas.id), "other_text": None, "quantity": "2"},
            {"part_id": str(cano.id), "other_text": None, "quantity": "1.5"},
            {"part_id": None, "other_text": "Cinta aisladora", "quantity": "1"},
        ],
    )

    primero = await _cerrar(mundo.celular, orden.id, cierre)
    reenvio = await _cerrar(mundo.celular, orden.id, cierre)
    stock = (await _call(admin, "GET", URL)).json()
    historial = (await _call(admin, "GET", f"{URL}/parts/{gas.id}/movements")).json()

    assert primero.status_code == 201, primero.text
    assert reenvio.status_code == 200
    assert _saldos(stock) == {
        ("Caño de cobre 1/4", "Camioneta 1"): "-1.500",
        ("Gas R410A", "Camioneta 1"): "-1.000",
    }
    assert all(item["has_negative"] for item in stock)
    uso = historial[0]
    assert (uso["kind"], uso["work_order_number"], uso["from_location_name"]) == (
        "usage",
        orden.number,
        "Camioneta 1",
    )
    async with SessionLocal() as session:
        usos = await session.scalar(
            select(func.count()).select_from(StockMovement).where(StockMovement.kind == "usage")
        )
    assert usos == 2


# Sin camioneta asignada, el cierre funciona y no mueve stock.
async def test_escuadrilla_sin_camioneta_cierra_sin_mover_stock(mundo: Mundo) -> None:
    gas, _, _ = await _materiales(mundo)
    orden = await _orden(mundo)

    response = await _cerrar(
        mundo.celular,
        orden.id,
        _resuelta(mundo, parts=[{"part_id": str(gas.id), "other_text": None, "quantity": "1"}]),
    )

    assert response.status_code == 201
    async with SessionLocal() as session:
        assert await session.scalar(select(func.count()).select_from(StockMovement)) == 0


# E08-04, criterio 4, y E08-05, criterio 2: la escuadrilla ve su camioneta, sin precios.
async def test_la_escuadrilla_ve_su_camioneta(mundo: Mundo) -> None:
    admin = await _admin()
    gas, _, _ = await _materiales(mundo)
    camioneta = await _ubicacion(
        admin, "Camioneta 1", kind="truck", crew_id=str(mundo.escuadrilla.id)
    )
    deposito = await _ubicacion(admin, "Depósito central")
    await _ingreso(admin, gas, camioneta, "3")
    await _ingreso(admin, gas, deposito, "50")

    response = await _call(mundo.celular, "GET", "/tech/stock")

    assert response.status_code == 200
    assert response.json() == {
        "location_name": "Camioneta 1",
        "items": [{"part_name": "Gas R410A", "unit": "kg", "quantity": "3.000"}],
    }


# E08-07, criterio 3, y permisos: el técnico no ve ni mueve el stock de la oficina;
# dirección lo ve pero no lo mueve.
@pytest.mark.parametrize("role", [UserRole.technician, UserRole.owner])
async def test_permisos(mundo: Mundo, role: UserRole) -> None:
    otro = make_user(email=f"{role.value}@ot-demo.com", role=role)
    await _seed([otro])
    gas, _, _ = await _materiales(mundo)

    consulta = await _call(otro, "GET", URL)
    historial = await _call(otro, "GET", f"{URL}/parts/{gas.id}/movements")
    alta = await _call(otro, "POST", f"{URL}/locations", {"kind": "warehouse", "name": "X"})
    ingreso = await _call(
        otro,
        "POST",
        f"{URL}/receipts",
        {"part_id": str(gas.id), "location_id": str(uuid.uuid4()), "quantity": "1"},
    )

    lectura = 403 if role == UserRole.technician else 200
    assert (consulta.status_code, historial.status_code) == (lectura, lectura)
    assert (alta.status_code, ingreso.status_code) == (403, 403)


async def test_cantidades_con_decimales_no_usan_float(mundo: Mundo) -> None:
    admin = await _admin()
    gas, _, _ = await _materiales(mundo)
    deposito = await _ubicacion(admin, "Depósito central")
    for cantidad in ("0.1", "0.2"):
        await _ingreso(admin, gas, deposito, cantidad)

    stock = (await _call(admin, "GET", URL)).json()

    assert Decimal(stock[0]["total"]) == Decimal("0.3")
