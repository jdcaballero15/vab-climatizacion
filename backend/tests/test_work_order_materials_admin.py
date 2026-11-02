"""E05-05 y E04-08: materiales de la orden en administración, total, aprobación y precio."""

import uuid
from collections.abc import AsyncGenerator
from datetime import timedelta
from decimal import Decimal
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select, text

from app.db.models.catalog import WorkType
from app.db.models.client import Client, ClientSite
from app.db.models.crew import Crew
from app.db.models.part import Part, PartPrice, PartUsage
from app.db.models.user import User, UserRole
from app.db.models.work_order import WorkOrder, WorkOrderClosure, WorkOrderEvent
from app.db.session import SessionLocal, engine
from app.domain.work_order import ClosureOutcome, OrderStatus, WorkOrderEventType
from app.main import app
from tests.factories import make_user
from tests.test_work_order_closure_admin import (
    AYER,
    ORDERS_URL,
    TABLES,
    Mundo,
    _auth,
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


@pytest.fixture
async def gas(mundo: Mundo) -> Part:
    return await _material("Gas R410A", "kg", "1000")


@pytest.fixture
async def cano(mundo: Mundo) -> Part:
    return await _material("Caño de cobre 1/4", "metro", "200")


async def _material(name: str, unit: str, price: str) -> Part:
    part = Part(name=name, unit=unit)
    await _seed([part])
    await _seed([PartPrice(part_id=part.id, list_price=Decimal(price))])
    return part


async def _visita(
    m: Mundo,
    orden: WorkOrder,
    lineas: list[tuple[Part | str, str]],
    outcome: ClosureOutcome = ClosureOutcome.done,
    dias_atras: int = 1,
) -> WorkOrderClosure:
    """Un cierre de la escuadrilla con sus materiales: (material u "Otro", cantidad)."""
    cierre = WorkOrderClosure(
        work_order_id=orden.id,
        closed_by=m.celular.id,
        closed_at=AYER - timedelta(days=dias_atras - 1),
        idempotency_key=uuid.uuid4(),
        outcome=outcome,
    )
    await _seed([cierre])
    await _seed(
        [
            PartUsage(
                work_order_id=orden.id,
                closure_id=cierre.id,
                part_id=item.id if isinstance(item, Part) else None,
                other_text=item if isinstance(item, str) else None,
                quantity=Decimal(cantidad),
                created_by=m.celular.id,
            )
            for item, cantidad in lineas
        ]
    )
    return cierre


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _url(orden: WorkOrder, extra: str = "") -> str:
    return f"{ORDERS_URL}/{orden.id}/materials{extra}"


async def _get(user: User, orden: WorkOrder) -> Response:
    async with _client() as client:
        return await client.get(_url(orden), headers=_auth(user))


async def _post(user: User, url: str, body: dict[str, Any] | None = None) -> Response:
    async with _client() as client:
        return await client.post(url, json=body or {}, headers=_auth(user))


async def _patch(user: User, url: str, body: dict[str, Any]) -> Response:
    async with _client() as client:
        return await client.patch(url, json=body, headers=_auth(user))


async def _set_price(admin: User, part: Part, price: str) -> None:
    async with _client() as client:
        response = await client.put(
            f"/admin/parts/{part.id}/price", json={"list_price": price}, headers=_auth(admin)
        )
    assert response.status_code == 200, response.text


async def _aprobar(admin: User, orden: WorkOrder) -> Response:
    return await _post(admin, f"{ORDERS_URL}/{orden.id}/approval")


def _linea(body: dict[str, Any], name: str) -> dict[str, Any]:
    return next(line for line in body["lines"] if line["name"] == name)


async def _eventos(orden: WorkOrder, tipo: WorkOrderEventType) -> list[WorkOrderEvent]:
    async with SessionLocal() as session:
        result = await session.scalars(
            select(WorkOrderEvent).where(
                WorkOrderEvent.work_order_id == orden.id, WorkOrderEvent.event_type == tipo
            )
        )
        return list(result.all())


# El total suma los materiales de todas las visitas, cada uno con su visita.
async def test_total_suma_todas_las_visitas(mundo: Mundo, gas: Part, cano: Part) -> None:
    orden = await _orden(mundo, OrderStatus.done)
    primera = await _visita(mundo, orden, [(gas, "1.5")], ClosureOutcome.needs_revisit, 3)
    segunda = await _visita(mundo, orden, [(cano, "3.2")])

    response = await _get(mundo.admin, orden)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["approved"] is False
    assert body["total"] == "2140.00"
    linea_gas = _linea(body, "Gas R410A")
    assert linea_gas["unit"] == "kg"
    assert linea_gas["quantity"] == "1.500"
    assert linea_gas["unit_price"] == "1000.00"
    assert linea_gas["subtotal"] == "1500.00"
    assert linea_gas["is_other"] is False
    assert linea_gas["added_by_name"] == "Celular 1"
    assert _linea(body, "Caño de cobre 1/4")["subtotal"] == "640.00"
    visitas = {line["name"]: line["visit_closed_at"] for line in body["lines"]}
    assert visitas["Gas R410A"][:10] == primera.closed_at.date().isoformat()
    assert visitas["Caño de cobre 1/4"][:10] == segunda.closed_at.date().isoformat()


async def test_otro_no_tiene_precio_ni_suma(mundo: Mundo, gas: Part) -> None:
    orden = await _orden(mundo, OrderStatus.done)
    await _visita(mundo, orden, [(gas, "1"), ("Cinta aisladora", "2")])

    body = (await _get(mundo.admin, orden)).json()

    otro = _linea(body, "Cinta aisladora")
    assert otro["is_other"] is True
    assert otro["unit_price"] is None
    assert otro["subtotal"] is None
    assert body["total"] == "1000.00"


async def test_sin_materiales_total_cero(mundo: Mundo) -> None:
    orden = await _orden(mundo, OrderStatus.done)

    body = (await _get(mundo.admin, orden)).json()

    assert body == {"approved": False, "approved_at": None, "lines": [], "total": "0.00"}


# Antes de aprobar, la orden toma el precio vigente de la lista.
async def test_cambio_de_precio_antes_de_aprobar_cambia_el_total(mundo: Mundo, gas: Part) -> None:
    orden = await _orden(mundo, OrderStatus.done)
    await _visita(mundo, orden, [(gas, "2")])

    await _set_price(mundo.admin, gas, "1500")

    assert (await _get(mundo.admin, orden)).json()["total"] == "3000.00"


# Al aprobar se estampa el precio: un cambio posterior de la lista no la toca.
async def test_cambio_de_precio_despues_de_aprobar_no_cambia_el_total(
    mundo: Mundo, gas: Part
) -> None:
    orden = await _orden(mundo, OrderStatus.done)
    await _visita(mundo, orden, [(gas, "2")])

    aprobada = await _aprobar(mundo.admin, orden)
    await _set_price(mundo.admin, gas, "5000")
    body = (await _get(mundo.admin, orden)).json()

    assert aprobada.status_code == 200, aprobada.text
    assert aprobada.json()["approved"] is True
    assert body["approved"] is True
    assert body["approved_at"] is not None
    assert body["total"] == "2000.00"
    async with SessionLocal() as session:
        uso = await session.scalar(select(PartUsage))
    assert uso is not None
    assert uso.unit_price == Decimal("1000.00")


async def test_aprobar_registra_el_evento_sin_cambiar_el_estado(mundo: Mundo, gas: Part) -> None:
    orden = await _orden(mundo, OrderStatus.done)
    await _visita(mundo, orden, [(gas, "1")])

    await _aprobar(mundo.admin, orden)

    eventos = await _eventos(orden, WorkOrderEventType.review_approved)
    assert len(eventos) == 1
    assert eventos[0].actor_id == mundo.admin.id
    assert eventos[0].to_status is None
    async with SessionLocal() as session:
        actual = await session.get(WorkOrder, orden.id)
    assert actual is not None
    assert actual.status == OrderStatus.done


# Administración corrige, agrega y saca líneas; cada cambio queda en la línea de tiempo.
async def test_admin_corrige_agrega_y_saca(mundo: Mundo, gas: Part, cano: Part) -> None:
    orden = await _orden(mundo, OrderStatus.done)
    await _visita(mundo, orden, [(gas, "1.5"), (cano, "3")])
    lineas = (await _get(mundo.admin, orden)).json()["lines"]
    id_gas = _linea({"lines": lineas}, "Gas R410A")["id"]
    id_cano = _linea({"lines": lineas}, "Caño de cobre 1/4")["id"]
    capacitor = await _material("Capacitor 35 uF", "unidad", "300")

    corregida = await _patch(mundo.admin, _url(orden, f"/{id_gas}"), {"quantity": "2"})
    agregada = await _post(
        mundo.admin, _url(orden), {"part_id": str(capacitor.id), "quantity": "1"}
    )
    sacada = await _post(mundo.admin, _url(orden, f"/{id_cano}/removal"))

    assert corregida.status_code == 200, corregida.text
    assert agregada.status_code == 201, agregada.text
    assert sacada.status_code == 200, sacada.text
    body = (await _get(mundo.admin, orden)).json()
    assert sorted(line["name"] for line in body["lines"]) == ["Capacitor 35 uF", "Gas R410A"]
    assert _linea(body, "Gas R410A")["quantity"] == "2.000"
    nueva = _linea(body, "Capacitor 35 uF")
    assert nueva["visit_closed_at"] is None
    assert nueva["added_by_name"] == "Admin Ficticia"
    assert body["total"] == "2300.00"
    eventos = await _eventos(orden, WorkOrderEventType.materials_changed)
    assert len(eventos) == 3
    assert {e.actor_id for e in eventos} == {mundo.admin.id}
    assert any(e.note == "Gas R410A: 1,5 -> 2 kg" for e in eventos)
    async with SessionLocal() as session:
        cano_uso = await session.scalar(select(PartUsage).where(PartUsage.part_id == cano.id))
    assert cano_uso is not None
    assert cano_uso.deleted_at is not None


async def test_admin_agrega_otro(mundo: Mundo) -> None:
    orden = await _orden(mundo, OrderStatus.done)

    response = await _post(mundo.admin, _url(orden), {"other_text": "Cinta", "quantity": "1"})

    assert response.status_code == 201, response.text
    assert _linea(response.json(), "Cinta")["is_other"] is True


@pytest.mark.parametrize(
    ("body", "status", "code"),
    [
        ({"quantity": "1"}, 422, "part_required"),
        ({"other_text": "Cinta", "part_id": "otro", "quantity": "1"}, 422, "part_ambiguous"),
        ({"part_id": "inactivo", "quantity": "1"}, 422, "part_not_available"),
    ],
)
async def test_agregar_linea_invalida(
    mundo: Mundo, gas: Part, body: dict[str, Any], status: int, code: str
) -> None:
    orden = await _orden(mundo, OrderStatus.done)
    viejo = await _material("Filtro viejo", "unidad", "1")
    async with SessionLocal() as session:
        actual = await session.get(Part, viejo.id)
        assert actual is not None
        actual.is_active = False
        await session.commit()
    if body.get("part_id") == "otro":
        body = {**body, "part_id": str(gas.id)}
    if body.get("part_id") == "inactivo":
        body = {**body, "part_id": str(viejo.id)}

    response = await _post(mundo.admin, _url(orden), body)

    assert response.status_code == status, response.text
    assert response.json()["detail"]["code"] == code


@pytest.mark.parametrize("cantidad", ["0", "-1", "1.2345"])
async def test_corregir_cantidad_invalida(mundo: Mundo, gas: Part, cantidad: str) -> None:
    orden = await _orden(mundo, OrderStatus.done)
    await _visita(mundo, orden, [(gas, "1")])
    linea = (await _get(mundo.admin, orden)).json()["lines"][0]

    response = await _patch(mundo.admin, _url(orden, f"/{linea['id']}"), {"quantity": cantidad})

    assert response.status_code == 422


async def test_linea_de_otra_orden_da_404(mundo: Mundo, gas: Part) -> None:
    orden = await _orden(mundo, OrderStatus.done)
    otra = await _orden(mundo, OrderStatus.done)
    await _visita(mundo, otra, [(gas, "1")])
    linea = (await _get(mundo.admin, otra)).json()["lines"][0]

    response = await _patch(mundo.admin, _url(orden, f"/{linea['id']}"), {"quantity": "2"})

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "material_line_not_found"


# "Otro" pasa a la lista: la línea toma el material y su precio.
async def test_pasar_otro_a_la_lista(mundo: Mundo) -> None:
    orden = await _orden(mundo, OrderStatus.done)
    await _visita(mundo, orden, [("cinta aisladora", "2")])
    linea = (await _get(mundo.admin, orden)).json()["lines"][0]
    cinta = await _material("Cinta aisladora", "unidad", "300")

    response = await _post(
        mundo.admin, _url(orden, f"/{linea['id']}/promotion"), {"part_id": str(cinta.id)}
    )

    assert response.status_code == 200, response.text
    promovida = _linea(response.json(), "Cinta aisladora")
    assert promovida["is_other"] is False
    assert promovida["part_id"] == str(cinta.id)
    assert promovida["subtotal"] == "600.00"
    assert response.json()["total"] == "600.00"


async def test_pasar_a_la_lista_una_que_no_es_otro(mundo: Mundo, gas: Part, cano: Part) -> None:
    orden = await _orden(mundo, OrderStatus.done)
    await _visita(mundo, orden, [(gas, "1")])
    linea = (await _get(mundo.admin, orden)).json()["lines"][0]

    response = await _post(
        mundo.admin, _url(orden, f"/{linea['id']}/promotion"), {"part_id": str(cano.id)}
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "line_not_other"


async def test_no_se_aprueba_con_otro_pendiente(mundo: Mundo, gas: Part) -> None:
    orden = await _orden(mundo, OrderStatus.done)
    await _visita(mundo, orden, [(gas, "1"), ("Cinta", "1")])

    response = await _aprobar(mundo.admin, orden)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "other_materials_pending"
    assert await _eventos(orden, WorkOrderEventType.review_approved) == []


@pytest.mark.parametrize("status", [OrderStatus.pending, OrderStatus.in_progress])
async def test_solo_se_aprueba_una_terminada(mundo: Mundo, status: OrderStatus) -> None:
    orden = await _orden(mundo, status)

    response = await _aprobar(mundo.admin, orden)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "order_not_done"


async def test_aprobar_dos_veces_da_conflicto(mundo: Mundo) -> None:
    orden = await _orden(mundo, OrderStatus.done)
    await _aprobar(mundo.admin, orden)

    response = await _aprobar(mundo.admin, orden)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "order_already_approved"


async def test_aprobada_no_se_edita(mundo: Mundo, gas: Part, cano: Part) -> None:
    orden = await _orden(mundo, OrderStatus.done)
    await _visita(mundo, orden, [(gas, "1")])
    linea = (await _get(mundo.admin, orden)).json()["lines"][0]
    await _aprobar(mundo.admin, orden)

    respuestas = [
        await _patch(mundo.admin, _url(orden, f"/{linea['id']}"), {"quantity": "2"}),
        await _post(mundo.admin, _url(orden), {"part_id": str(cano.id), "quantity": "1"}),
        await _post(mundo.admin, _url(orden, f"/{linea['id']}/removal")),
        await _post(
            mundo.admin, _url(orden, f"/{linea['id']}/promotion"), {"part_id": str(cano.id)}
        ),
    ]

    assert [r.status_code for r in respuestas] == [409, 409, 409, 409]
    assert {r.json()["detail"]["code"] for r in respuestas} == {"order_already_approved"}


async def test_cancelada_no_se_edita(mundo: Mundo, gas: Part) -> None:
    orden = await _orden(mundo, OrderStatus.cancelled)

    response = await _post(mundo.admin, _url(orden), {"part_id": str(gas.id), "quantity": "1"})

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "order_not_editable"


async def test_orden_inexistente_da_404(mundo: Mundo) -> None:
    async with _client() as client:
        response = await client.get(
            f"{ORDERS_URL}/{uuid.uuid4()}/materials", headers=_auth(mundo.admin)
        )

    assert response.status_code == 404


@pytest.mark.parametrize("role", [UserRole.technician, UserRole.owner])
async def test_tecnico_y_direccion_reciben_403(mundo: Mundo, gas: Part, role: UserRole) -> None:
    orden = await _orden(mundo, OrderStatus.done)
    await _visita(mundo, orden, [(gas, "1")])
    linea = uuid.uuid4()
    otro = make_user(email=f"{role.value}@ot-demo.com", role=role)
    await _seed([otro])

    respuestas = [
        await _get(otro, orden),
        await _post(otro, _url(orden), {"part_id": str(gas.id), "quantity": "1"}),
        await _patch(otro, _url(orden, f"/{linea}"), {"quantity": "2"}),
        await _post(otro, _url(orden, f"/{linea}/removal")),
        await _post(otro, _url(orden, f"/{linea}/promotion"), {"part_id": str(gas.id)}),
        await _aprobar(otro, orden),
    ]

    assert [r.status_code for r in respuestas] == [403] * 6
