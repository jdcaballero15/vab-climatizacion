"""Baja y restauración (E03-07, E12-02), unificar clientes (E03-08), pasar un equipo a otro
cliente (E03-09) y la ficha del equipo (E03-05)."""

import uuid
from collections.abc import AsyncGenerator, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select, text

from app.db.models.audit import AuditEvent
from app.db.models.catalog import EquipmentType, WorkType
from app.db.models.client import Client, ClientContact, ClientSite
from app.db.models.equipment import Equipment, EquipmentTransfer
from app.db.models.legacy_reference import LegacyReference
from app.db.models.part import Part, PartUsage
from app.db.models.user import User, UserRole
from app.db.models.work_order import WorkOrder, WorkOrderEvent
from app.db.session import SessionLocal, engine
from app.domain.work_order import OrderStatus, WorkOrderEventType
from app.main import app
from tests.factories import make_user, make_work_order
from tests.test_work_order_closure_admin import TABLES as CLOSURE_TABLES
from tests.test_work_order_closure_admin import _auth

TABLES = [
    *CLOSURE_TABLES,
    AuditEvent.__table__,
    EquipmentTransfer.__table__,
    LegacyReference.__table__,
]
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
    "workshop_stage",
    "check_result",
)


@pytest.fixture
async def schema() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(User.metadata.create_all, tables=TABLES)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.drop_all, tables=list(reversed(TABLES)))
        for enum_type in ENUMS:
            await conn.execute(text(f"DROP TYPE IF EXISTS {enum_type}"))
        await conn.execute(text("DROP SEQUENCE IF EXISTS work_order_number_seq"))


@dataclass
class Mundo:
    admin: User
    farmacia: Client
    heladeria: Client
    deposito: ClientSite
    local: ClientSite
    split: Equipment
    reparacion: WorkType


async def _seed(items: Sequence[object]) -> None:
    async with SessionLocal() as session:
        session.add_all(list(items))
        await session.commit()


@pytest.fixture
async def mundo(schema: None) -> Mundo:
    admin = make_user(email="admin@ot-demo.com", role=UserRole.admin, full_name="Admin Ficticia")
    farmacia = Client(id=uuid.uuid4(), number="10642", name="Farmacia Del Sol")
    heladeria = Client(id=uuid.uuid4(), number="10643", name="Heladería La Inventada")
    aire = EquipmentType(name="Aire acondicionado", code_prefix="EA")
    reparacion = WorkType(name="Reparación")
    await _seed([admin, farmacia, heladeria, aire, reparacion])
    deposito = ClientSite(client_id=farmacia.id, label="Depósito", address="Ruta 9 km 5")
    local = ClientSite(client_id=heladeria.id, label="Local", address="Avenida Belgrano 1200")
    await _seed([deposito, local])
    split = Equipment(
        client_site_id=deposito.id,
        equipment_type_id=aire.id,
        internal_code="EA1064201",
        location_note="Oficina de ventas",
    )
    await _seed([split, ClientContact(client_id=farmacia.id, name="Rosa Ficticia")])
    return Mundo(admin, farmacia, heladeria, deposito, local, split, reparacion)


async def _call(user: User, method: str, url: str, body: dict[str, Any] | None = None) -> Response:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.request(method, url, json=body, headers=_auth(user))


async def _orden(m: Mundo, status: OrderStatus, *, equipo: Equipment | None = None) -> WorkOrder:
    orden = make_work_order(client_site=m.deposito, work_type=m.reparacion, status=status)
    orden.equipment_id = equipo.id if equipo else None
    await _seed([orden])
    await _seed(
        [
            WorkOrderEvent(
                work_order_id=orden.id,
                event_type=WorkOrderEventType.created,
                to_status=OrderStatus.pending,
            )
        ]
    )
    return orden


# E03-07, criterio 1 y 3: la baja saca al cliente de la lista, conserva su ficha e historial
# y queda auditada; criterio 2: se restaura.
async def test_dar_de_baja_y_restaurar_un_cliente(mundo: Mundo) -> None:
    m = mundo
    terminada = await _orden(m, OrderStatus.done)
    url = f"/admin/clients/{m.farmacia.id}"

    baja = await _call(m.admin, "POST", f"{url}/deactivation")
    activos = (await _call(m.admin, "GET", "/admin/clients")).json()
    de_baja = (await _call(m.admin, "GET", "/admin/clients?deleted=true")).json()
    ficha = await _call(m.admin, "GET", url)
    historial = (await _call(m.admin, "GET", f"{url}/orders")).json()
    restaurado = await _call(m.admin, "POST", f"{url}/restoration")
    auditoria = (await _call(m.admin, "GET", f"{url}/audit")).json()

    assert baja.status_code == 200
    assert baja.json()["deleted_at"] is not None
    assert [c["number"] for c in activos["items"]] == ["10643"]
    assert [c["number"] for c in de_baja["items"]] == ["10642"]
    assert ficha.status_code == 200
    assert [o["number"] for o in historial["items"]] == [terminada.number]
    assert restaurado.json()["deleted_at"] is None
    assert [(a["action"], a["actor_name"]) for a in auditoria] == [
        ("deactivated", "Admin Ficticia"),
        ("restored", "Admin Ficticia"),
    ]


# Criterio 4: con órdenes abiertas no se da de baja, y dice cuáles.
async def test_no_se_da_de_baja_con_ordenes_abiertas(mundo: Mundo) -> None:
    m = mundo
    abierta = await _orden(m, OrderStatus.assigned)

    response = await _call(m.admin, "POST", f"/admin/clients/{m.farmacia.id}/deactivation")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "client_has_open_orders"
    assert f"N° {abierta.number}" in response.json()["detail"]["message"]


# Criterio 1: dado de baja, no se ofrece para órdenes nuevas.
async def test_cliente_de_baja_no_recibe_ordenes_nuevas(mundo: Mundo) -> None:
    m = mundo
    await _call(m.admin, "POST", f"/admin/clients/{m.farmacia.id}/deactivation")

    response = await _call(
        m.admin,
        "POST",
        "/admin/orders",
        {
            "client_id": str(m.farmacia.id),
            "client_site_id": str(m.deposito.id),
            "work_type_id": str(m.reparacion.id),
            "channel": "phone",
            "description": "No enfría",
        },
    )

    assert response.status_code == 404


# E03-08: antes de unificar se ve qué se mueve; al unificar pasa todo al que queda, los
# equipos conservan su código y el que se va queda de baja indicando en cuál se unificó.
async def test_unificar_clientes(mundo: Mundo) -> None:
    m = mundo
    orden = await _orden(m, OrderStatus.assigned, equipo=m.split)
    url = f"/admin/clients/{m.farmacia.id}"

    preview = await _call(m.admin, "GET", f"{url}/merge-preview?into_client_id={m.heladeria.id}")
    merge = await _call(m.admin, "POST", f"{url}/merge", {"into_client_id": str(m.heladeria.id)})
    se_fue = (await _call(m.admin, "GET", url)).json()
    restaurar = await _call(m.admin, "POST", f"{url}/restoration")
    equipos = (await _call(m.admin, "GET", f"/admin/clients/{m.heladeria.id}/equipment")).json()
    contactos = (await _call(m.admin, "GET", f"/admin/clients/{m.heladeria.id}/contacts")).json()

    assert preview.status_code == 200
    assert {k: preview.json()[k] for k in ("sites", "contacts", "equipment", "orders")} == {
        "sites": 1,
        "contacts": 1,
        "equipment": 1,
        "orders": 1,
    }
    assert merge.status_code == 200
    assert se_fue["deleted_at"] is not None
    assert se_fue["merged_into"]["number"] == "10643"
    assert restaurar.json()["detail"]["code"] == "client_merged"
    assert [e["internal_code"] for e in equipos] == ["EA1064201"]
    assert [c["name"] for c in contactos] == ["Rosa Ficticia"]
    async with SessionLocal() as session:
        movida = await session.get(WorkOrder, orden.id)
        assert movida is not None and movida.client_id == m.heladeria.id


async def test_no_se_unifica_un_cliente_en_si_mismo(mundo: Mundo) -> None:
    m = mundo
    response = await _call(
        m.admin,
        "POST",
        f"/admin/clients/{m.farmacia.id}/merge",
        {"into_client_id": str(m.farmacia.id)},
    )
    assert response.status_code == 422


# E03-09: pasa con código nuevo del cliente nuevo, queda el traslado y se lo encuentra por
# el código anterior. Las órdenes anteriores siguen en el cliente de origen.
async def test_pasar_un_equipo_a_otro_cliente(mundo: Mundo) -> None:
    m = mundo
    anterior = await _orden(m, OrderStatus.done, equipo=m.split)

    response = await _call(
        m.admin,
        "POST",
        f"/admin/equipment/{m.split.id}/transfer",
        {"client_site_id": str(m.local.id)},
    )
    busqueda = (await _call(m.admin, "GET", "/admin/search?q=EA1064201")).json()
    ficha = (await _call(m.admin, "GET", f"/admin/equipment/{m.split.id}/file")).json()

    assert response.status_code == 200
    assert response.json()["internal_code"] == "EA1064301"
    assert response.json()["client_site_id"] == str(m.local.id)
    assert [e["internal_code"] for e in busqueda["equipment"]] == ["EA1064301"]
    assert ficha["client_name"] == "Heladería La Inventada"
    traslado = ficha["transfers"][0]
    assert (traslado["from_code"], traslado["to_code"]) == ("EA1064201", "EA1064301")
    assert traslado["from_client_name"] == "Farmacia Del Sol"
    assert traslado["transferred_by_name"] == "Admin Ficticia"
    assert [(o["number"], o["before_transfer"]) for o in ficha["orders"]] == [
        (anterior.number, True)
    ]
    async with SessionLocal() as session:
        orden = await session.get(WorkOrder, anterior.id)
        assert orden is not None and orden.client_id == m.farmacia.id


@pytest.mark.parametrize("caso", ["mismo_cliente", "inactivo", "inexistente"])
async def test_traslado_a_un_domicilio_invalido(mundo: Mundo, caso: str) -> None:
    m = mundo
    otro = ClientSite(client_id=m.farmacia.id, label="Otro", address="Calle 2")
    inactivo = ClientSite(
        client_id=m.heladeria.id, label="Cerrado", address="Calle 3", is_active=False
    )
    await _seed([otro, inactivo])
    destino = {"mismo_cliente": otro.id, "inactivo": inactivo.id, "inexistente": uuid.uuid4()}

    response = await _call(
        m.admin,
        "POST",
        f"/admin/equipment/{m.split.id}/transfer",
        {"client_site_id": str(destino[caso])},
    )

    assert response.status_code == {"mismo_cliente": 422, "inactivo": 422, "inexistente": 404}[caso]


# E03-05: la ficha trae los trabajos con repuestos, y distingue los importados de Persat.
async def test_ficha_del_equipo_con_trabajos_repuestos_e_importados(mundo: Mundo) -> None:
    m = mundo
    nueva = await _orden(m, OrderStatus.done, equipo=m.split)
    importada = await _orden(m, OrderStatus.done, equipo=m.split)
    filtro = Part(name="Filtro ficticio", unit="unidad")
    await _seed([filtro])
    await _seed(
        [
            PartUsage(
                work_order_id=nueva.id,
                part_id=filtro.id,
                quantity=Decimal("2"),
                created_by=m.admin.id,
            ),
            LegacyReference(entity="work_order", entity_id=importada.id, legacy_id="P-1"),
        ]
    )

    ficha = (await _call(m.admin, "GET", f"/admin/equipment/{m.split.id}/file")).json()

    por_numero = {o["number"]: o for o in ficha["orders"]}
    assert por_numero[nueva.number]["materials"] == ["Filtro ficticio x 2 unidad"]
    assert por_numero[nueva.number]["imported"] is False
    assert por_numero[importada.number]["imported"] is True
    assert "price" not in str(ficha)


# E03-07 para equipos: baja (no con órdenes abiertas), lista de dados de baja y restauración.
async def test_baja_y_restauracion_de_un_equipo(mundo: Mundo) -> None:
    m = mundo
    abierta = await _orden(m, OrderStatus.in_progress, equipo=m.split)
    url = f"/admin/equipment/{m.split.id}"

    bloqueada = await _call(m.admin, "POST", f"{url}/deactivation")
    async with SessionLocal() as session:
        orden = await session.get(WorkOrder, abierta.id)
        assert orden is not None
        orden.status = OrderStatus.done
        await session.commit()
    baja = await _call(m.admin, "POST", f"{url}/deactivation")
    lista = f"/admin/clients/{m.farmacia.id}/equipment"
    activos = (await _call(m.admin, "GET", lista)).json()
    de_baja = (await _call(m.admin, "GET", f"{lista}?deleted=true")).json()
    restaurado = await _call(m.admin, "POST", f"{url}/restoration")

    assert bloqueada.status_code == 409
    assert f"N° {abierta.number}" in bloqueada.json()["detail"]["message"]
    assert baja.status_code == 200
    assert activos == []
    assert [e["internal_code"] for e in de_baja] == ["EA1064201"]
    assert restaurado.json()["deleted_at"] is None
    async with SessionLocal() as session:
        acciones = (
            await session.scalars(
                select(AuditEvent.action)
                .where(AuditEvent.entity_id == m.split.id)
                .order_by(AuditEvent.occurred_at)
            )
        ).all()
    assert list(acciones) == ["deactivated", "restored"]


# Solo administración da de baja, restaura, unifica y traslada; el técnico no ve la ficha.
@pytest.mark.parametrize("role", [UserRole.technician, UserRole.owner])
async def test_tecnico_y_direccion_no_cambian_nada(mundo: Mundo, role: UserRole) -> None:
    m = mundo
    otro = make_user(email=f"{role.value}@ot-demo.com", role=role)
    await _seed([otro])
    cliente = f"/admin/clients/{m.farmacia.id}"
    equipo = f"/admin/equipment/{m.split.id}"

    respuestas = [
        await _call(otro, "POST", f"{cliente}/deactivation"),
        await _call(otro, "POST", f"{cliente}/restoration"),
        await _call(otro, "POST", f"{cliente}/merge", {"into_client_id": str(m.heladeria.id)}),
        await _call(otro, "POST", f"{equipo}/deactivation"),
        await _call(otro, "POST", f"{equipo}/transfer", {"client_site_id": str(m.local.id)}),
    ]
    ficha = await _call(otro, "GET", f"{equipo}/file")

    assert {r.status_code for r in respuestas} == {403}
    assert ficha.status_code == (403 if role == UserRole.technician else 200)
