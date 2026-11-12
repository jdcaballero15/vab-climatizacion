"""E12-01: auditoría de cambios con quién, cuándo, qué entidad y las diferencias."""

from collections.abc import AsyncGenerator, Sequence
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import text

from app.db.models.catalog import WorkType
from app.db.models.client import Client
from app.db.models.user import User, UserRole
from app.db.session import SessionLocal, engine
from app.main import app
from tests.factories import make_user
from tests.test_work_order_closure_admin import _auth

TABLES = [User.__table__, WorkType.__table__, Client.__table__]


@pytest.fixture
async def schema() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.create_all, tables=TABLES)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.drop_all, tables=list(reversed(TABLES)))
        for enum_type in ("user_role", "client_segment", "tax_condition"):
            await conn.execute(text(f"DROP TYPE IF EXISTS {enum_type}"))


async def _seed(items: Sequence[object]) -> None:
    async with SessionLocal() as session:
        session.add_all(list(items))
        await session.commit()


async def _call(user: User, method: str, url: str, body: dict[str, Any] | None = None) -> Response:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.request(method, url, json=body, headers=_auth(user))


@pytest.fixture
async def admin(schema: None) -> User:
    user = make_user(email="admin@ot-demo.com", full_name="Admin Ficticia")
    await _seed([user])
    return user


# Criterio 1: alta y cambio quedan con usuario, fecha, entidad, acción y diferencias.
async def test_registra_alta_y_cambio_con_diferencias(admin: User) -> None:
    alta = await _call(admin, "POST", "/admin/work-types", {"name": "Instalación"})
    tipo = alta.json()["id"]
    await _call(admin, "PATCH", f"/admin/work-types/{tipo}", {"name": "Instalación nueva"})

    page = (await _call(admin, "GET", "/admin/audit?entity=work_type")).json()

    acciones = [(item["action"], item["actor_name"]) for item in page["items"]]
    assert acciones == [("updated", "Admin Ficticia"), ("created", "Admin Ficticia")]
    assert page["items"][0]["changes"]["name"] == ["Instalación", "Instalación nueva"]
    assert page["items"][1]["entity_id"] == tipo


# Criterio 2: se filtra por usuario y fecha.
async def test_filtros(admin: User) -> None:
    otro = make_user(email="otra@ot-demo.com", full_name="Otra Ficticia")
    await _seed([otro])
    await _call(admin, "POST", "/admin/work-types", {"name": "Retiro"})
    await _call(otro, "POST", "/admin/work-types", {"name": "Devolución"})

    de_otra = (await _call(admin, "GET", f"/admin/audit?actor_id={otro.id}")).json()
    manana = (await _call(admin, "GET", "/admin/audit?date_from=2999-01-01")).json()

    assert [i["changes"]["name"][1] for i in de_otra["items"]] == ["Devolución"]
    assert manana["total"] == 0


# Criterio 4: el CUIT o DNI del cliente se enmascara.
async def test_datos_personales_enmascarados(admin: User) -> None:
    alta = await _call(
        admin, "POST", "/admin/clients", {"name": "Hotel Ficticio", "tax_id": "30712345674"}
    )
    assert alta.status_code == 201, alta.text

    page = (await _call(admin, "GET", "/admin/audit?entity=client")).json()

    assert page["items"][0]["changes"]["tax_id"] == [None, "***"]
    assert "30712345674" not in str(page)


# Criterio 3 y permisos: dirección la ve; el técnico no; nadie la modifica.
async def test_solo_lectura_y_permisos(admin: User) -> None:
    direccion = make_user(email="dir@ot-demo.com", role=UserRole.owner)
    tecnico = make_user(email="tec@ot-demo.com", role=UserRole.technician)
    await _seed([direccion, tecnico])

    lectura = await _call(direccion, "GET", "/admin/audit")
    tecnico_lee = await _call(tecnico, "GET", "/admin/audit")
    borrar = await _call(admin, "DELETE", "/admin/audit")

    assert lectura.status_code == 200
    assert tecnico_lee.status_code == 403
    assert borrar.status_code == 405


# Los cambios fuera de un pedido autenticado (importaciones, datos de prueba) no se auditan.
async def test_sin_usuario_no_registra(admin: User) -> None:
    await _seed([WorkType(name="Cargado por script"), Client(number="1", name="Script")])

    page = (await _call(admin, "GET", "/admin/audit")).json()

    assert page["total"] == 0
