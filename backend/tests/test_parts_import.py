from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from sqlalchemy import select, text

from app.db.models.part import Part, PartPrice
from app.db.models.user import User
from app.db.session import SessionLocal, engine
from app.parts_import import read_csv
from app.services.parts import import_parts

# E02-05: carga inicial de la lista de materiales, todos con precio 0.

TABLES = [User.__table__, Part.__table__, PartPrice.__table__]


@pytest.fixture
async def schema() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.create_all, tables=TABLES)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.drop_all, tables=list(reversed(TABLES)))
        await conn.execute(text("DROP TYPE IF EXISTS user_role"))


async def test_importar_crea_los_materiales_en_cero(schema: None) -> None:
    async with SessionLocal() as session:
        result = await import_parts(session, [("Gas R410A", "kg"), ("Caño de cobre 1/4", "metro")])

    assert (result.created, result.skipped) == (2, 0)
    async with SessionLocal() as session:
        parts = (await session.scalars(select(Part).order_by(Part.name))).all()
        prices = (await session.scalars(select(PartPrice))).all()
    assert [(p.name, p.unit) for p in parts] == [
        ("Caño de cobre 1/4", "metro"),
        ("Gas R410A", "kg"),
    ]
    assert {p.list_price for p in prices} == {0}
    assert {p.created_by for p in prices} == {None}


async def test_importar_dos_veces_no_duplica(schema: None) -> None:
    rows = [("Gas R410A", "kg"), ("Capacitor 35 uF", "unidad")]
    async with SessionLocal() as session:
        await import_parts(session, rows)
    async with SessionLocal() as session:
        result = await import_parts(session, [("gas r410a", "kg"), ("Capacitor 35 uF", "unidad")])

    assert (result.created, result.skipped) == (0, 2)


async def test_unidad_vacia_queda_como_unidad(schema: None) -> None:
    async with SessionLocal() as session:
        await import_parts(session, [("Cinta aisladora", "")])
    async with SessionLocal() as session:
        part = await session.scalar(select(Part))
    assert part is not None
    assert part.unit == "unidad"


def test_leer_csv_con_encabezado(tmp_path: Path) -> None:
    archivo = tmp_path / "materiales.csv"
    archivo.write_text("nombre,unidad\nGas R410A,kg\n  ,metro\nCapacitor,\n", encoding="utf-8")

    assert read_csv(archivo) == [("Gas R410A", "kg"), ("Capacitor", "")]


def test_leer_csv_sin_columna_nombre_falla(tmp_path: Path) -> None:
    archivo = tmp_path / "materiales.csv"
    archivo.write_text("material,unidad\nGas,kg\n", encoding="utf-8")

    with pytest.raises(ValueError, match="nombre"):
        read_csv(archivo)
