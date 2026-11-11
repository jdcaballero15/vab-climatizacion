"""E02-08: importar y exportar catálogos por CSV."""

from collections.abc import AsyncGenerator, Sequence
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import select, text

from app.db.models.catalog import EquipmentType, Failure, Repair, WorkType
from app.db.models.part import Part
from app.db.models.user import User, UserRole
from app.db.session import SessionLocal, engine
from app.main import app
from tests.factories import make_user
from tests.test_work_order_closure_admin import _auth

TABLES = [
    User.__table__,
    WorkType.__table__,
    EquipmentType.__table__,
    Failure.__table__,
    Repair.__table__,
    Part.__table__,
]


@pytest.fixture
async def admin() -> AsyncGenerator[User, None]:
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.create_all, tables=TABLES)
    user = make_user(email="admin@ot-demo.com")
    await _seed([user, EquipmentType(name="Aire acondicionado"), Part(name="Gas R410A", unit="kg")])
    yield user
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.drop_all, tables=list(reversed(TABLES)))
        await conn.execute(text("DROP TYPE IF EXISTS user_role"))


async def _seed(items: Sequence[object]) -> None:
    async with SessionLocal() as session:
        session.add_all(list(items))
        await session.commit()


async def _call(user: User, method: str, url: str, body: dict[str, Any] | None = None) -> Response:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.request(method, url, json=body, headers=_auth(user))


MATERIALES = "nombre,unidad,codigo,activo\nGas R410A,kg,G-1,sí\nCaño de cobre,metro,,sí\n"


# Criterio 1: vista previa con altas y cambios, sin aplicar.
async def test_vista_previa(admin: User) -> None:
    response = await _call(
        admin, "POST", "/admin/catalog-csv/parts/preview", {"content": MATERIALES}
    )

    body = response.json()
    assert [r["name"] for r in body["creates"]] == ["Caño de cobre"]
    assert body["changes"] == [{"row": 2, "name": "Gas R410A", "detail": "code: - → G-1"}]
    assert body["applied"] is False
    async with SessionLocal() as session:
        assert len((await session.scalars(select(Part))).all()) == 1


# Criterio 2: con un error se informa la fila y no se aplica nada.
async def test_con_errores_no_aplica_nada(admin: User) -> None:
    contenido = (
        "nombre,tipo_de_equipo,activo\nNo enfría,,sí\nPierde agua,Heladera,sí\nRuido,,quizás\n"
    )

    response = await _call(
        admin, "POST", "/admin/catalog-csv/failures/apply", {"content": contenido}
    )

    body = response.json()
    assert body["applied"] is False
    assert [(e["row"], e["detail"]) for e in body["errors"]] == [
        (3, "no existe el tipo de equipo «Heladera»"),
        (4, "activo tiene que ser sí o no"),
    ]
    async with SessionLocal() as session:
        assert (await session.scalars(select(Failure))).all() == []


# Sin errores se aplica todo; la exportación tiene las mismas columnas y vuelve a entrar
# sin cambios (criterio 3).
async def test_aplicar_y_exportar(admin: User) -> None:
    aplicado = await _call(admin, "POST", "/admin/catalog-csv/parts/apply", {"content": MATERIALES})
    exportado = await _call(admin, "GET", "/admin/catalog-csv/parts")
    de_nuevo = await _call(
        admin, "POST", "/admin/catalog-csv/parts/preview", {"content": exportado.text}
    )

    assert aplicado.json()["applied"] is True
    assert exportado.headers["content-type"].startswith("text/csv")
    assert exportado.text.splitlines() == [
        "nombre,unidad,codigo,activo",
        "Caño de cobre,metro,,sí",
        "Gas R410A,kg,G-1,sí",
    ]
    assert de_nuevo.json()["unchanged"] == 2
    assert de_nuevo.json()["creates"] == de_nuevo.json()["changes"] == []


async def test_reparaciones_con_su_falla(admin: User) -> None:
    await _call(
        admin,
        "POST",
        "/admin/catalog-csv/failures/apply",
        {"content": "nombre,tipo_de_equipo,activo\nNo enfría,Aire acondicionado,sí\n"},
    )
    response = await _call(
        admin,
        "POST",
        "/admin/catalog-csv/repairs/apply",
        {"content": "nombre,falla,tipo_de_equipo,activo\nCarga de gas,No enfría,,sí\n"},
    )

    assert response.json()["applied"] is True
    async with SessionLocal() as session:
        reparacion = await session.scalar(select(Repair))
        falla = await session.scalar(select(Failure))
    assert reparacion is not None and falla is not None
    assert reparacion.failure_id == falla.id


async def test_columnas_faltantes(admin: User) -> None:
    response = await _call(
        admin, "POST", "/admin/catalog-csv/parts/preview", {"content": "nombre\nGas\n"}
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_csv"


async def test_solo_administracion(admin: User) -> None:
    tecnico = make_user(email="tec@ot-demo.com", role=UserRole.technician)
    await _seed([tecnico])
    response = await _call(tecnico, "GET", "/admin/catalog-csv/parts")
    assert response.status_code == 403
