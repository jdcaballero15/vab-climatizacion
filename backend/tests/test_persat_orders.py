"""E11-03 historial de órdenes de Persat, E11-04 informe de calidad y E11-05 lotes.

Los archivos son ficticios, con el formato de la exportación: un .xls que es una tabla
HTML con tablas anidadas en algunas celdas.
"""

import csv
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from sqlalchemy import func, select, text

from app import persat_import as cli
from app.db.models.catalog import EquipmentType, WorkType
from app.db.models.client import Client, ClientSite
from app.db.models.import_batch import ImportBatch
from app.db.models.legacy_reference import LegacyReference
from app.db.models.work_order import WorkOrder, WorkOrderEvent
from app.db.session import SessionLocal, engine
from app.domain.work_order import OrderSource, OrderStatus
from app.services import persat_batches
from app.services.persat_import import CLIENT_HEADERS, EQUIPMENT_HEADERS, import_persat, read_rows
from app.services.persat_orders import read_order_files
from tests.test_persat_import import (
    CLIENT_COLUMNS,
    EQUIPMENT_COLUMNS,
    _client,
    _equipment,
    _xlsx,
)
from tests.test_work_order_closure_admin import TABLES as CLOSURE_TABLES

# Las tablas de los tests del cierre (órdenes completas, para pedirlas por la API) más los
# lotes y las referencias.
TABLES = [*CLOSURE_TABLES, ImportBatch.__table__, LegacyReference.__table__]
ENUMS = (
    "user_role",
    "client_segment",
    "tax_condition",
    "order_status",
    "order_kind",
    "order_source",
    "order_channel",
    "workshop_stage",
    "closure_outcome",
    "equipment_condition",
    "not_done_reason",
    "cancel_reason",
    "no_signature_reason",
    "signature_purpose",
)
COMMON = [
    "#Num.",
    "Estado",
    "Fecha",
    "Causa de Cierre",
    "Cliente",
    "Nro. de Cliente",
    "Tipo",
    "Grupo",
    "Nombre",
    "Email",
    "Telefono",
    "Altura",
    "Localidad",
    "Provincia",
    "Tipo",
    "Etiquetas",
    "Tecnico",
]


@pytest.fixture
async def schema() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Client.metadata.create_all, tables=TABLES)
    async with SessionLocal() as session:
        session.add(EquipmentType(name="Aire acondicionado", code_prefix="EA"))
        session.add(EquipmentType(name="Heladera comercial", code_prefix="EH"))
        session.add(EquipmentType(name="Heladera familiar", code_prefix="EH"))
        session.add(WorkType(name="Reparación"))
        await session.commit()
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Client.metadata.drop_all, tables=list(reversed(TABLES)))
        for enum_type in ENUMS:
            await conn.execute(text(f"DROP TYPE IF EXISTS {enum_type}"))
        await conn.execute(text("DROP SEQUENCE IF EXISTS work_order_number_seq"))


def _cell(value: str | list[list[str]]) -> str:
    if isinstance(value, str):
        return f"<td>{value}</td>"
    rows = "".join("<tr>" + "".join(f"<td>{v}</td>" for v in row) + "</tr>" for row in value)
    return f"<td><table>{rows}</table></td>"


def _form(path: Path, extra: list[str], rows: list[list[str | list[list[str]]]]) -> None:
    head = "".join(f"<th>{name}</th>" for name in COMMON + extra)
    body = "".join("<tr>" + "".join(_cell(v) for v in row) + "</tr>" for row in rows)
    path.write_text(
        '<html xmlns:o="urn:schemas-microsoft-com:office:office"><body>'
        f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></body></html>",
        encoding="utf-8",
    )


def _common(num: str, estado: str, fecha: str, cliente: str, etiquetas: str) -> list[str]:
    return [num, estado, fecha, "", "x", cliente, "", "", "", "", "", "", "", "", "", etiquetas,
            "CUADRILLA 1"]  # fmt: skip


@pytest.fixture
def ordenes(tmp_path: Path) -> Path:
    folder = tmp_path / "ordenes"
    folder.mkdir()
    _form(
        folder / "ordenes_de_trabajo.xls",
        ["REFERIDO A ORDEN DE TRABAJO N°", "RECLAMO A REPARAR", "", "OBSERVACIONES:"],
        [
            _common("5001", "CERRADA_OK", "07-10-2026 08:00", "10642", "REPARACION | Ana Ficticia")
            + ["12", "No enfría", [["N/A", "", ""]], "Se cargó gas"],
            _common("5002", "CANCELADA", "08-10-2026 09:30", "10642", "Beto Inventado")
            + ["", "Pierde agua", [["N/A"]], "N/A"],
            _common("5003", "CERRADA_OK", "31-02-2026 08:00", "10642", "")
            + ["", "Fecha mala", [["N/A"]], ""],
            _common("5004", "CERRADA_OK", "09-10-2026 08:00", "99999", "")
            + ["", "Cliente que no está", [["N/A"]], ""],
        ],
    )
    _form(
        folder / "mm_aire_split.xls",
        ["FECHA", "", "Observaciones"],
        [
            _common("6001", "INFORME", "10-10-2026 10:00", "10642", "Ana Ficticia")
            + ["10-10-2026", [["EA1064201", "Hotel", "Aire Acondicionado"]], "Limpieza de filtros"],
        ],
    )
    return folder


async def _base(tmp_path: Path) -> None:
    """Clientes y equipos ya importados, como en la migración real."""
    clientes = _xlsx(tmp_path / "c.xlsx", CLIENT_COLUMNS, [_client(10642, "Hotel Ficticio")])
    equipos = _xlsx(tmp_path / "e.xlsx", EQUIPMENT_COLUMNS, [_equipment("EA1064201", "10642")])
    async with SessionLocal() as session:
        await import_persat(
            session,
            clients=read_rows(clientes, CLIENT_HEADERS),
            equipment=read_rows(equipos, EQUIPMENT_HEADERS),
            apply=True,
            run_by="Prueba",
        )


async def _import_orders(folder: Path, *, apply: bool = True) -> cli.ImportReport:
    async with SessionLocal() as session:
        return await import_persat(
            session,
            clients=None,
            equipment=None,
            orders=read_order_files(folder),
            apply=apply,
            run_by="Prueba",
        )


async def _orders() -> list[WorkOrder]:
    async with SessionLocal() as session:
        return list(
            (await session.scalars(select(WorkOrder).order_by(WorkOrder.description))).all()
        )


# E11-03, criterio 1: en modo prueba dice cuántas y a qué clientes y equipos, sin guardar.
async def test_modo_prueba_informa_sin_guardar(schema: None, tmp_path: Path, ordenes: Path) -> None:
    await _base(tmp_path)

    report = await _import_orders(ordenes, apply=False)

    assert report.orders.created == 3
    assert report.orders.with_equipment == 1
    assert report.orders.clients == {"10642"}
    assert report.orders.by_work_type == {"Reparación": 2, "Mantenimiento": 1}
    assert [(i.ref, i.reason) for i in report.orders.errors] == [
        ("ordenes_de_trabajo orden 5003", "fecha inválida"),
        ("ordenes_de_trabajo orden 5004", "el cliente no está importado"),
    ]
    assert await _orders() == []


# Criterios 2 y 4: quedan como historial importado, de solo lectura (source persat), con la
# fecha de Persat, el equipo si lo hay y el detalle en texto.
async def test_importa_el_historial(schema: None, tmp_path: Path, ordenes: Path) -> None:
    await _base(tmp_path)

    report = await _import_orders(ordenes)
    again = await _import_orders(ordenes)

    assert report.orders.created == 3
    assert again.orders.created == 0 and again.orders.existing == 3
    orders = await _orders()
    assert {o.source for o in orders} == {OrderSource.persat}
    by_number = {o.description.split("\n")[0]: o for o in orders if o.description}
    reparacion = by_number["Persat N° 5001 · cerrada"]
    assert reparacion.status == OrderStatus.done
    assert reparacion.equipment_id is None
    assert reparacion.description == (
        "Persat N° 5001 · cerrada\nCuadrilla: CUADRILLA 1\nTécnicos: Ana Ficticia\n"
        "No enfría\nSe cargó gas"
    )
    assert by_number["Persat N° 5002 · cancelada"].status == OrderStatus.cancelled
    mantenimiento = by_number["Persat N° 6001 · hecha sin cerrar"]
    assert mantenimiento.equipment_id is not None
    async with SessionLocal() as session:
        fecha = await session.scalar(
            select(WorkOrderEvent.occurred_at).where(WorkOrderEvent.work_order_id == reparacion.id)
        )
        tipo = await session.scalar(select(WorkType).where(WorkType.name == "Mantenimiento"))
    assert fecha is not None and fecha.isoformat().startswith("2026-10-07T11:00")
    # El tipo que no existía se crea desactivado: no se ofrece para órdenes nuevas.
    assert tipo is not None and tipo.is_active is False


# E11-04: el informe de calidad trae cada problema con fila y sugerencia, y los posibles
# duplicados de clientes; solo números, sin nombres.
async def test_informe_de_calidad(schema: None, tmp_path: Path, ordenes: Path) -> None:
    clientes = _xlsx(
        tmp_path / "c.xlsx",
        CLIENT_COLUMNS,
        [
            _client(10642, "Farmacia Del Sol"),
            _client(10643, "FARMACIA DEL SOL"),
            _client(10644, "Hotel Ficticio", Dirección=""),
        ],
    )
    async with SessionLocal() as session:
        report = await import_persat(
            session,
            clients=read_rows(clientes, CLIENT_HEADERS),
            equipment=None,
            orders=read_order_files(ordenes),
            apply=False,
        )
    path = tmp_path / "informe.csv"

    count = cli.write_quality_report(report, path)

    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assert count == len(rows)
    sin_direccion = next(r for r in rows if r["problema"] == "sin dirección")
    assert sin_direccion["sugerencia"] == "Cargar la dirección del domicilio en el sistema."
    duplicado = next(r for r in rows if r["tipo"] == "posible duplicado")
    assert duplicado["referencia"] == "10642, 10643"
    assert "Farmacia" not in path.read_text(encoding="utf-8")


# E11-05: el lote queda registrado; deshacerlo da de baja lo creado y nada más, y después
# se puede volver a importar.
async def test_deshacer_un_lote(schema: None, tmp_path: Path, ordenes: Path) -> None:
    await _base(tmp_path)
    report = await _import_orders(ordenes)
    assert report.batch_id is not None

    async with SessionLocal() as session:
        batches = await persat_batches.list_batches(session)
        batch = await persat_batches.undo_batch(session, report.batch_id)
    again = await _import_orders(ordenes)

    assert len(batches) == 2
    assert batches[0].summary == "clientes: 0, equipos: 0, órdenes: 3"
    assert batches[0].run_by == "Prueba"
    assert batch.undone_at is not None
    assert again.orders.created == 3
    async with SessionLocal() as session:
        vivos = await session.scalar(
            select(func.count()).select_from(Client).where(Client.deleted_at.is_(None))
        )
        borradas = await session.scalar(
            select(func.count()).select_from(WorkOrder).where(WorkOrder.deleted_at.is_not(None))
        )
    assert vivos == 1
    assert borradas == 3


# Criterio 3: si lo importado ya tiene órdenes nuevas, no se deshace y dice cuáles.
async def test_no_se_deshace_un_lote_en_uso(schema: None, tmp_path: Path) -> None:
    await _base(tmp_path)
    async with SessionLocal() as session:
        primer_lote = (await persat_batches.list_batches(session))[0]
        client_id = await session.scalar(select(Client.id))
        site_id = await session.scalar(select(ClientSite.id))
        work_type_id = await session.scalar(select(WorkType.id))
        assert client_id and site_id and work_type_id
        nueva = WorkOrder(
            client_id=client_id,
            client_site_id=site_id,
            work_type_id=work_type_id,
            status=OrderStatus.pending,
        )
        session.add(nueva)
        await session.commit()
        numero = nueva.number

    async with SessionLocal() as session:
        with pytest.raises(persat_batches.BatchInUseError) as error:
            await persat_batches.undo_batch(session, primer_lote.id)

    assert f"N° {numero}" in error.value.message


async def test_lote_inexistente(schema: None) -> None:
    async with SessionLocal() as session:
        with pytest.raises(persat_batches.BatchNotFoundError):
            await persat_batches.undo_batch(session, uuid.uuid4())


# Criterios 3 y 4: no entran en el panel, se marcan como importadas en el historial del
# cliente y no se pueden modificar.
async def test_historial_importado_fuera_del_panel_y_de_solo_lectura(
    schema: None, tmp_path: Path, ordenes: Path
) -> None:
    from httpx import ASGITransport, AsyncClient

    from app.main import app
    from tests.factories import make_user
    from tests.test_work_order_closure_admin import _auth

    await _base(tmp_path)
    await _import_orders(ordenes)
    admin = make_user(email="admin@ot-demo.com")
    async with SessionLocal() as session:
        session.add(admin)
        await session.commit()
        client_id = await session.scalar(select(Client.id))
        cancelada = await session.scalar(
            select(WorkOrder).where(WorkOrder.status == OrderStatus.cancelled)
        )
    assert cancelada is not None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        panel = await http.get("/admin/orders?status=done", headers=_auth(admin))
        historial = await http.get(f"/admin/clients/{client_id}/orders", headers=_auth(admin))
        equipo = await http.put(
            f"/admin/orders/{cancelada.id}/equipment",
            json={"equipment_id": None},
            headers=_auth(admin),
        )

    assert panel.json()["total"] == 0
    items = historial.json()["items"]
    assert len(items) == 3
    assert all(item["imported"] for item in items)
    assert items[0]["description"].startswith("Persat N° ")
    assert equipo.status_code == 409
