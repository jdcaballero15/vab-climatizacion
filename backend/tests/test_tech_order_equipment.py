"""E05-15: la escuadrilla agrega el equipo de una orden que no tiene."""

import uuid
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select

from app.db.models.catalog import EquipmentType, WorkType
from app.db.models.client import ClientSite
from app.db.models.crew import Crew
from app.db.models.equipment import Equipment
from app.db.models.user import User, UserRole
from app.db.models.work_order import WorkOrder, WorkOrderEvent
from app.db.session import SessionLocal
from app.domain.work_order import OrderStatus
from app.main import app
from tests.factories import make_user
from tests.test_tech_order_start import _auth, _orden, _seed
from tests.test_tech_order_start import celular as celular
from tests.test_tech_order_start import escuadrilla as escuadrilla
from tests.test_tech_order_start import otra_escuadrilla as otra_escuadrilla
from tests.test_tech_order_start import reparacion as reparacion
from tests.test_tech_order_start import schema as schema
from tests.test_tech_order_start import sede as sede


@pytest.fixture
async def aire(schema: None) -> EquipmentType:
    item = EquipmentType(name="Aire acondicionado", code_prefix="EA")
    await _seed([item])
    return item


def _datos(tipo: EquipmentType, **extra: Any) -> dict[str, Any]:
    return {"equipment_type_id": str(tipo.id), "location_note": "Living", **extra}


async def _agregar(user: User, order_id: object, body: dict[str, Any]) -> Response:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.post(
            f"/tech/orders/{order_id}/equipment", json=body, headers=_auth(user)
        )


async def _tipos(user: User) -> Response:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get("/tech/equipment-types", headers=_auth(user))


async def _equipos(sede: ClientSite) -> list[Equipment]:
    async with SessionLocal() as session:
        rows = await session.scalars(select(Equipment).where(Equipment.client_site_id == sede.id))
        return list(rows.all())


async def _orden_y_eventos(order_id: uuid.UUID) -> tuple[WorkOrder, list[WorkOrderEvent]]:
    async with SessionLocal() as session:
        orden = await session.get(WorkOrder, order_id)
        eventos = await session.scalars(
            select(WorkOrderEvent).where(WorkOrderEvent.work_order_id == order_id)
        )
        assert orden is not None
        return orden, list(eventos.all())


# Criterios 1 y 2: el equipo queda en el domicilio de la orden, asociado y en la línea de tiempo.
@pytest.mark.parametrize("estado", [OrderStatus.assigned, OrderStatus.in_progress])
async def test_agrega_el_equipo_a_una_orden_sin_equipo(
    celular: User,
    escuadrilla: Crew,
    sede: ClientSite,
    reparacion: WorkType,
    aire: EquipmentType,
    estado: OrderStatus,
) -> None:
    orden = await _orden(sede, reparacion, escuadrilla, estado)
    datos = _datos(
        aire,
        brand="Marca Ficticia",
        model="X1",
        capacity_frigorias=3000,
        refrigerant="R410A",
        power_supply="220",
    )

    response = await _agregar(celular, orden.id, datos)

    assert response.status_code == 201, response.text
    assert response.json()["equipment"] == {
        "location_note": "Living",
        "equipment_type_name": "Aire acondicionado",
        "brand": "Marca Ficticia",
        "model": "X1",
        "capacity_frigorias": 3000,
        "refrigerant": "R410A",
        "power_supply": "220",
    }
    (equipo,) = await _equipos(sede)
    assert equipo.internal_code == "EA1064201"
    guardada, eventos = await _orden_y_eventos(orden.id)
    assert guardada.equipment_id == equipo.id
    assert guardada.status == estado
    (evento,) = [e for e in eventos if e.event_type == "equipment_changed"]
    assert evento.actor_id == celular.id
    assert evento.note == "Equipo: sin equipo -> EA1064201 (cargado por la escuadrilla)"


# Criterio 3: con equipo no se agrega otro.
async def test_orden_con_equipo_da_409(
    celular: User, escuadrilla: Crew, sede: ClientSite, reparacion: WorkType, aire: EquipmentType
) -> None:
    previo = Equipment(
        client_site_id=sede.id,
        equipment_type_id=aire.id,
        internal_code="EA1064201",
        location_note="Habitación 12",
    )
    await _seed([previo])
    orden = await _orden(sede, reparacion, escuadrilla, equipment=previo)

    response = await _agregar(celular, orden.id, _datos(aire))

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "order_has_equipment"
    assert len(await _equipos(sede)) == 1


# Criterio 4: de otra escuadrilla, cerrada o inexistente, como si no existiera.
@pytest.mark.parametrize("caso", ["otra", "cerrada", "inexistente"])
async def test_orden_ajena_cerrada_o_inexistente_da_404(
    celular: User,
    escuadrilla: Crew,
    otra_escuadrilla: Crew,
    sede: ClientSite,
    reparacion: WorkType,
    aire: EquipmentType,
    caso: str,
) -> None:
    if caso == "otra":
        order_id: object = (await _orden(sede, reparacion, otra_escuadrilla)).id
    elif caso == "cerrada":
        order_id = (await _orden(sede, reparacion, escuadrilla, OrderStatus.done)).id
    else:
        order_id = uuid.uuid4()

    response = await _agregar(celular, order_id, _datos(aire))

    assert response.status_code == 404
    assert await _equipos(sede) == []


# Criterio 5: faltantes, datos fuera de lista o tipo inactivo.
@pytest.mark.parametrize(
    "cambio",
    [
        {"location_note": "  "},
        {"equipment_type_id": None},
        {"refrigerant": "R999"},
        {"capacity_frigorias": 0},
        {"client_site_id": str(uuid.uuid4())},
    ],
)
async def test_datos_invalidos_dan_422(
    celular: User,
    escuadrilla: Crew,
    sede: ClientSite,
    reparacion: WorkType,
    aire: EquipmentType,
    cambio: dict[str, Any],
) -> None:
    orden = await _orden(sede, reparacion, escuadrilla)

    response = await _agregar(celular, orden.id, {**_datos(aire), **cambio})

    assert response.status_code == 422
    assert await _equipos(sede) == []


async def test_tipo_inactivo_da_422(
    celular: User, escuadrilla: Crew, sede: ClientSite, reparacion: WorkType
) -> None:
    viejo = EquipmentType(name="Tipo viejo", is_active=False)
    await _seed([viejo])
    orden = await _orden(sede, reparacion, escuadrilla)

    response = await _agregar(celular, orden.id, _datos(viejo))

    assert response.status_code == 422
    assert response.json()["detail"]["field"] == "equipment_type_id"


# Criterio 6: administración y dirección no usan la ruta del técnico.
@pytest.mark.parametrize("role", [UserRole.admin, UserRole.owner])
async def test_admin_y_direccion_reciben_403(
    escuadrilla: Crew,
    sede: ClientSite,
    reparacion: WorkType,
    aire: EquipmentType,
    role: UserRole,
) -> None:
    oficina = make_user(email=f"{role.value}@ot-demo.com", role=role)
    await _seed([oficina])
    orden = await _orden(sede, reparacion, escuadrilla)

    assert (await _agregar(oficina, orden.id, _datos(aire))).status_code == 403
    assert (await _tipos(oficina)).status_code == 403


# Criterio 7: solo los tipos activos, con id y nombre.
async def test_tipos_activos_para_el_tecnico(celular: User, aire: EquipmentType) -> None:
    await _seed([EquipmentType(name="Tipo viejo", is_active=False)])

    response = await _tipos(celular)

    assert response.status_code == 200
    assert response.json() == [{"id": str(aire.id), "name": "Aire acondicionado"}]
