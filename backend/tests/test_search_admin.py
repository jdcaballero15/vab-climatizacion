import uuid
from collections.abc import AsyncGenerator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import text

from app.core.security import create_access_token
from app.db.models.catalog import EquipmentType
from app.db.models.client import Client, ClientContact, ClientSite
from app.db.models.equipment import Equipment, EquipmentTransfer
from app.db.models.user import User, UserRole
from app.db.session import SessionLocal, engine
from app.main import app
from tests.factories import make_user

# E03-06: buscar clientes y equipos desde la oficina.
TABLES = [
    User.__table__,
    Client.__table__,
    ClientSite.__table__,
    ClientContact.__table__,
    EquipmentType.__table__,
    Equipment.__table__,
    # Para encontrar un equipo por su código anterior a un traslado (E03-09).
    EquipmentTransfer.__table__,
]
URL = "/admin/search"


@pytest.fixture
async def schema() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        # Lo crea la migración; acá las tablas salen del modelo.
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(User.metadata.create_all, tables=TABLES)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.drop_all, tables=list(reversed(TABLES)))
        for enum_type in ("user_role", "client_segment", "tax_condition"):
            await conn.execute(text(f"DROP TYPE IF EXISTS {enum_type}"))


@dataclass
class Mundo:
    admin: User
    tecnico: User
    farmacia: Client
    heladeria: Client
    split: Equipment
    freezer: Equipment


async def _seed(items: Sequence[object]) -> None:
    async with SessionLocal() as session:
        session.add_all(list(items))
        await session.commit()


@pytest.fixture
async def mundo(schema: None) -> Mundo:
    admin = make_user(email="admin@ot-demo.com", role=UserRole.admin)
    tecnico = make_user(email="esc1@ot-demo.com", role=UserRole.technician)
    farmacia = Client(id=uuid.uuid4(), number="10642", name="Farmacia Del Sol")
    heladeria = Client(id=uuid.uuid4(), number="10643", name="Heladería La Inventada")
    aire = EquipmentType(name="Aire acondicionado")
    await _seed([admin, tecnico, farmacia, heladeria, aire])
    deposito = ClientSite(client_id=farmacia.id, label="Depósito", address="Ruta 9 km 5")
    local = ClientSite(client_id=heladeria.id, label="Local", address="Avenida Belgrano 1200")
    await _seed([deposito, local])
    contacto = ClientContact(client_id=heladeria.id, name="Rosa Ficticia", phone="(0385) 421-5566")
    split = Equipment(
        client_site_id=deposito.id,
        equipment_type_id=aire.id,
        internal_code="EA1064201",
        location_note="Oficina de ventas",
        brand="Marca Ficticia",
        model="Split 3000",
        serial_number="SN-998877",
    )
    freezer = Equipment(
        client_site_id=local.id,
        equipment_type_id=aire.id,
        internal_code="EF1064301",
        location_note="Cámara de helados",
    )
    await _seed([contacto, split, freezer])
    return Mundo(
        admin=admin,
        tecnico=tecnico,
        farmacia=farmacia,
        heladeria=heladeria,
        split=split,
        freezer=freezer,
    )


def _auth(user: User) -> dict[str, str]:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


async def _buscar(user: User, q: str, **params: object) -> Response:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(URL, params={"q": q, **params}, headers=_auth(user))


async def _ids(m: Mundo, q: str, **params: object) -> tuple[list[str], list[str]]:
    response = await _buscar(m.admin, q, **params)
    assert response.status_code == 200, response.text
    body = response.json()
    return [c["id"] for c in body["clients"]], [e["id"] for e in body["equipment"]]


# Criterio 1: sin mayúsculas ni acentos, por nombre, número, dirección o teléfono.
@pytest.mark.parametrize("q", ["heladeria", "HELADERÍA", "10643", "belgrano", "421 5566"])
async def test_encuentra_clientes(mundo: Mundo, q: str) -> None:
    clientes, _ = await _ids(mundo, q)

    assert clientes == [str(mundo.heladeria.id)]


# Criterio 1: tolera errores menores de tipeo.
async def test_tolera_errores_de_tipeo(mundo: Mundo) -> None:
    clientes, _ = await _ids(mundo, "farmasia")

    assert clientes == [str(mundo.farmacia.id)]


@pytest.mark.parametrize("q", ["EA1064201", "ea1064", "sn-998877", "split 3000", "oficina ventas"])
async def test_encuentra_equipos(mundo: Mundo, q: str) -> None:
    _, equipos = await _ids(mundo, q)

    assert equipos == [str(mundo.split.id)]


async def test_el_equipo_trae_su_cliente_y_domicilio(mundo: Mundo) -> None:
    body = (await _buscar(mundo.admin, "EA1064201")).json()

    assert body["equipment"] == [
        {
            "id": str(mundo.split.id),
            "internal_code": "EA1064201",
            "location_note": "Oficina de ventas",
            "equipment_type_name": "Aire acondicionado",
            "brand": "Marca Ficticia",
            "model": "Split 3000",
            "client_id": str(mundo.farmacia.id),
            "client_name": "Farmacia Del Sol",
            "site_label": "Depósito",
            "site_address": "Ruta 9 km 5",
            "deleted": False,
        }
    ]


async def test_el_cliente_trae_numero_y_un_domicilio(mundo: Mundo) -> None:
    body = (await _buscar(mundo.admin, "farmacia")).json()

    assert body["clients"] == [
        {
            "id": str(mundo.farmacia.id),
            "number": "10642",
            "name": "Farmacia Del Sol",
            "address": "Ruta 9 km 5",
            "deleted": False,
        }
    ]


async def test_sin_coincidencias(mundo: Mundo) -> None:
    assert await _ids(mundo, "zzzzqqq") == ([], [])


# Criterio 3: las bajas solo con "Incluir bajas".
async def test_las_bajas_solo_si_se_piden(mundo: Mundo) -> None:
    async with SessionLocal() as session:
        await session.execute(
            text("UPDATE equipment SET deleted_at = :now WHERE id = :id"),
            {"now": datetime.now(UTC), "id": mundo.freezer.id},
        )
        await session.commit()

    assert await _ids(mundo, "EF1064301") == ([], [])
    _, equipos = await _ids(mundo, "EF1064301", include_deleted=True)
    assert equipos == [str(mundo.freezer.id)]
    body = (await _buscar(mundo.admin, "EF1064301", include_deleted=True)).json()
    assert body["equipment"][0]["deleted"] is True


async def test_pide_al_menos_dos_letras(mundo: Mundo) -> None:
    response = await _buscar(mundo.admin, "a")

    assert response.status_code == 422


async def test_el_tecnico_no_busca(mundo: Mundo) -> None:
    response = await _buscar(mundo.tecnico, "farmacia")

    assert response.status_code == 403


async def test_direccion_busca(mundo: Mundo) -> None:
    direccion = make_user(email="direccion@ot-demo.com", role=UserRole.owner)
    await _seed([direccion])

    response = await _buscar(direccion, "farmacia")

    assert response.status_code == 200
