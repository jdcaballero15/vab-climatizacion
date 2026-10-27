"""Importación de clientes y equipos de Persat (E11-01, E11-02), con planillas ficticias."""

from collections.abc import AsyncGenerator, Sequence
from pathlib import Path

import pytest
from openpyxl import Workbook
from sqlalchemy import func, select, text

from app import persat_import as cli
from app.db.base import Base
from app.db.models.catalog import EquipmentType
from app.db.models.client import Client, ClientContact, ClientSegment, ClientSite, TaxCondition
from app.db.models.equipment import Equipment
from app.db.models.legacy_reference import LegacyReference
from app.db.session import SessionLocal, engine
from app.services.persat_import import (
    CLIENT_HEADERS,
    EQUIPMENT_HEADERS,
    ImportReport,
    Issue,
    PersatFileError,
    import_persat,
    read_rows,
)

TABLES = [
    Client.__table__,
    ClientSite.__table__,
    ClientContact.__table__,
    EquipmentType.__table__,
    Equipment.__table__,
    LegacyReference.__table__,
]
CLIENT_COLUMNS = [
    "Nro. de Cliente",
    "Razón Social",
    "Descripción",
    "Tipo",
    "Grupo",
    "Dirección",
    "Latitud",
    "Longitud",
    "Inicio de Jornada [HH:mm]",
    "Fin de Jornada [HH:mm]",
    "Tiempo de Servicio [min]",
    "Nombre",
    "Email",
    "Telefono",
    "Altura",
    "Localidad",
    "Provincia",
]
EQUIPMENT_COLUMNS = [
    "Numero de Serie",
    "Nro. de Cliente",
    "Razón Social",
    "UBICACION",
    "TIPO",
    "SUB TIPO",
    "MODELO",
    "MARCA",
    "POTENCIA",
    "GAS REFRIGERANTE",
    "TENSION DE ALIMENTACION",
]


def _client(number: object, name: str, **values: object) -> dict[str, object]:
    base = {"Nro. de Cliente": number, "Razón Social": name, "Dirección": "Calle Falsa 123"}
    return base | values


def _equipment(code: str, number: str, **values: object) -> dict[str, object]:
    defaults = {
        "Numero de Serie": code,
        "Nro. de Cliente": number,
        "UBICACION": "Oficina",
        "TIPO": "A.AC.",
        "SUB TIPO": "SPLIT",
        "MARCA": "CARRIER",
        "POTENCIA": "3000FG",
    }
    return defaults | values


CLIENTES = [
    _client(
        10642,
        "Hotel Ficticio",
        Tipo="HOTELES",
        Descripción="30712345674",
        Nombre="Recepción",
        Email="Recepcion@Ficticio.com",
        Telefono=3815550000.0,
        Latitud=-27.8,
    ),
    _client("CLI -00123", "Comercio Inventado", Tipo="COMERCIOS", Descripción="Consumidor Final"),
    _client(10500, "Particular Ficticio", Tipo="PARTICULARES", Descripción="Piso 3 depto B"),
    _client(10377, "Depósito propio", Tipo="DEPOSITO"),
    _client(10161, "Oficina propia", Tipo="ADMINISTRACION"),
    _client("CLP - 9999", "Cliente Persat", Tipo="Cliente"),
]
EQUIPOS = [
    _equipment("EA1064201", "10642", **{"GAS REFRIGERANTE": "R410", "MODELO": "Frio Solo"}),
    _equipment("EA1064202", "10642", UBICACION=""),
    _equipment("EA0012301", "CLI-00123"),
    _equipment("EA0012301", "10500"),
    _equipment("EA9999901", "99999"),
]


async def _seed(items: Sequence[object]) -> None:
    async with SessionLocal() as session:
        session.add_all(list(items))
        await session.commit()


@pytest.fixture
async def schema() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Client.metadata.create_all, tables=TABLES)
    await _seed(
        [
            EquipmentType(name="Aire acondicionado", code_prefix="EA"),
            EquipmentType(name="Heladera comercial", code_prefix="EH"),
            EquipmentType(name="Heladera familiar", code_prefix="EH"),
        ]
    )
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Client.metadata.drop_all, tables=list(reversed(TABLES)))
        await conn.execute(text("DROP TYPE IF EXISTS client_segment"))
        await conn.execute(text("DROP TYPE IF EXISTS tax_condition"))


def _xlsx(path: Path, columns: list[str], rows: list[dict[str, object]]) -> Path:
    book = Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.append(columns)
    for row in rows:
        sheet.append([row.get(column) for column in columns])
    # Persat deja filas vacías al final.
    sheet.append([None] * len(columns))
    book.save(path)
    return path


@pytest.fixture
def clientes_xlsx(tmp_path: Path) -> Path:
    return _xlsx(tmp_path / "clientes.xlsx", CLIENT_COLUMNS, CLIENTES)


@pytest.fixture
def equipos_xlsx(tmp_path: Path) -> Path:
    return _xlsx(tmp_path / "equipos.xlsx", EQUIPMENT_COLUMNS, EQUIPOS)


async def _import(
    clients: Path | None = None, equipment: Path | None = None, *, apply: bool = True
) -> ImportReport:
    async with SessionLocal() as session:
        return await import_persat(
            session,
            clients=read_rows(clients, CLIENT_HEADERS) if clients else None,
            equipment=read_rows(equipment, EQUIPMENT_HEADERS) if equipment else None,
            apply=apply,
        )


async def _count(model: type[Base]) -> int:
    async with SessionLocal() as session:
        return await session.scalar(select(func.count()).select_from(model)) or 0


async def _clients() -> dict[str, Client]:
    async with SessionLocal() as session:
        return {c.number: c for c in (await session.execute(select(Client))).scalars()}


async def _equipment_by_code() -> dict[str, Equipment]:
    async with SessionLocal() as session:
        result = await session.execute(select(Equipment))
        return {e.internal_code: e for e in result.scalars()}


# ---------- E11-01 Clientes ----------


# Criterio 1: en modo prueba informa qué crearía, sin guardar nada.
async def test_clientes_modo_prueba_no_guarda(schema: None, clientes_xlsx: Path) -> None:
    report = await _import(clientes_xlsx, apply=False)

    assert not report.applied
    assert report.clients.created == 3
    assert report.clients.existing == 0
    assert await _count(Client) == 0
    assert await _count(LegacyReference) == 0


# Criterio 2: se crean los clientes y cada uno guarda su referencia a Persat.
async def test_clientes_se_crean_con_su_referencia(schema: None, clientes_xlsx: Path) -> None:
    report = await _import(clientes_xlsx)

    assert report.clients.created == 3
    clientes = await _clients()
    assert set(clientes) == {"10642", "CLI-00123", "10500"}
    async with SessionLocal() as session:
        refs = (
            await session.execute(select(LegacyReference).where(LegacyReference.entity == "client"))
        ).scalars()
        assert {(r.legacy_id, r.entity_id) for r in refs} == {
            (number, client.id) for number, client in clientes.items()
        }


async def test_clientes_con_las_reglas_de_limpieza(schema: None, clientes_xlsx: Path) -> None:
    await _import(clientes_xlsx)

    clientes = await _clients()
    hotel = clientes["10642"]
    assert (hotel.name, hotel.segment, hotel.tax_id) == (
        "Hotel Ficticio",
        ClientSegment.hotel,
        "30712345674",
    )
    assert clientes["CLI-00123"].tax_condition == TaxCondition.final_consumer
    assert clientes["10500"].segment == ClientSegment.private_person
    async with SessionLocal() as session:
        sites = {
            s.client_id: s for s in (await session.execute(select(ClientSite))).scalars().all()
        }
        contacts = (await session.execute(select(ClientContact))).scalars().all()
    assert len(sites) == 3
    assert sites[hotel.id].address == "Calle Falsa 123"
    assert sites[clientes["10500"].id].reference == "Piso 3 depto B"
    # Solo el hotel tiene datos de contacto.
    assert [(c.client_id, c.name, c.email, c.phone) for c in contacts] == [
        (hotel.id, "Recepción", "recepcion@ficticio.com", "3815550000")
    ]


# Criterio 3: repetir la importación no duplica.
async def test_clientes_segunda_importacion_no_duplica(schema: None, clientes_xlsx: Path) -> None:
    await _import(clientes_xlsx)
    report = await _import(clientes_xlsx)

    assert (report.clients.created, report.clients.existing) == (0, 3)
    assert await _count(Client) == 3
    assert await _count(ClientSite) == 3
    assert await _count(ClientContact) == 1


# Criterio 4: una fila inválida se informa con su número y el motivo.
async def test_clientes_fila_invalida_se_informa(schema: None, tmp_path: Path) -> None:
    path = _xlsx(
        tmp_path / "c.xlsx",
        CLIENT_COLUMNS,
        [_client(1, "Uno"), _client(2, ""), _client(1, "Uno repetido")],
    )

    report = await _import(path)

    assert report.clients.created == 1
    assert report.clients.errors == [
        Issue(3, "cliente 2", "sin razón social"),
        Issue(4, "cliente 1", "repetido en el archivo"),
    ]


async def test_cliente_cargado_a_mano_con_el_mismo_numero(
    schema: None, clientes_xlsx: Path
) -> None:
    await _seed([Client(number="10642", name="Cargado a mano")])

    report = await _import(clientes_xlsx)

    assert Issue(2, "cliente 10642", "ya hay un cliente con ese número cargado a mano") in (
        report.clients.errors
    )
    assert (await _clients())["10642"].name == "Cargado a mano"


# Criterio 5: los registros internos y de prueba no se migran y figuran en el informe.
async def test_registros_internos_y_de_prueba_no_se_migran(
    schema: None, clientes_xlsx: Path
) -> None:
    report = await _import(clientes_xlsx)

    assert report.clients.skipped == [
        Issue(5, "cliente 10377", "registro interno (DEPOSITO)"),
        Issue(6, "cliente 10161", "registro interno (ADMINISTRACION)"),
        Issue(7, "cliente CLP-9999", "registro de prueba"),
    ]
    assert not {"10377", "10161", "CLP-9999"} & set(await _clients())


async def test_cliente_sin_numero_recibe_el_siguiente_y_queda_para_revisar(
    schema: None, tmp_path: Path
) -> None:
    path = _xlsx(
        tmp_path / "c.xlsx", CLIENT_COLUMNS, [_client(None, "Sin número"), _client(10642, "Otro")]
    )

    report = await _import(path)
    again = await _import(path)

    assert (await _clients())["10643"].name == "Sin número"
    assert report.clients.to_review == [
        Issue(2, "cliente 10643", "no tenía número en Persat: se le asignó uno nuevo")
    ]
    assert (again.clients.created, again.clients.existing) == (0, 2)


async def test_archivo_sin_las_columnas_de_persat(schema: None, tmp_path: Path) -> None:
    path = _xlsx(tmp_path / "otro.xlsx", ["Nombre", "Apellido"], [])

    with pytest.raises(PersatFileError, match="le faltan las columnas: Nro. de Cliente"):
        read_rows(path, CLIENT_HEADERS)


# ---------- E11-02 Equipos ----------


# Criterio 1: en modo prueba informa cuántos crearía y cuáles no se asocian a un cliente.
async def test_equipos_modo_prueba(schema: None, clientes_xlsx: Path, equipos_xlsx: Path) -> None:
    report = await _import(clientes_xlsx, equipos_xlsx, apply=False)

    assert report.equipment.created == 4
    assert report.equipment.errors == [
        Issue(6, "equipo EA9999901 (cliente 99999)", "no se puede asociar a un cliente importado")
    ]
    assert await _count(Equipment) == 0


# Criterios 2 y 3: asociado a su cliente y domicilio, con su código, ubicación y referencia.
async def test_equipo_asociado_con_su_codigo_y_referencia(
    schema: None, clientes_xlsx: Path, equipos_xlsx: Path
) -> None:
    await _import(clientes_xlsx, equipos_xlsx)

    equipos = await _equipment_by_code()
    hotel = (await _clients())["10642"]
    async with SessionLocal() as session:
        site = (
            await session.execute(select(ClientSite).where(ClientSite.client_id == hotel.id))
        ).scalar_one()
        ref = (
            await session.execute(
                select(LegacyReference).where(LegacyReference.legacy_id == "10642/EA1064201")
            )
        ).scalar_one()
        aire = (
            await session.execute(
                select(EquipmentType).where(EquipmentType.name == "Aire acondicionado")
            )
        ).scalar_one()
    equipo = equipos["EA1064201"]
    assert equipo.client_site_id == site.id
    assert equipo.equipment_type_id == aire.id
    assert (equipo.location_note, equipo.brand) == ("Oficina", "Carrier")
    assert equipo.notes == "Split. Frío solo. 3000 frigorías. R-410A."
    assert (ref.entity, ref.entity_id) == ("equipment", equipo.id)


# Criterio 4: repetir la importación no duplica equipos.
async def test_equipos_segunda_importacion_no_duplica(
    schema: None, clientes_xlsx: Path, equipos_xlsx: Path
) -> None:
    await _import(clientes_xlsx, equipos_xlsx)
    report = await _import(clientes_xlsx, equipos_xlsx)

    assert (report.equipment.created, report.equipment.existing) == (0, 4)
    assert await _count(Equipment) == 4


# Criterio 5: un código repetido recibe uno nuevo, conserva el de Persat y se informa.
async def test_codigo_repetido_recibe_uno_nuevo(
    schema: None, clientes_xlsx: Path, equipos_xlsx: Path
) -> None:
    report = await _import(clientes_xlsx, equipos_xlsx)

    equipos = await _equipment_by_code()
    nuevos = {code: e for code, e in equipos.items() if "Código de Persat" in (e.notes or "")}
    # Con la regla del sistema (prefijo, número de cliente y correlativo), el primero vuelve
    # a dar el mismo código: ahora es único.
    assert set(nuevos) == {"EA0012301", "EA1050001"}
    for equipo in nuevos.values():
        assert equipo.notes is not None and equipo.notes.endswith("Código de Persat: EA0012301.")
    async with SessionLocal() as session:
        legacy_ids = set(
            (
                await session.execute(
                    select(LegacyReference.legacy_id).where(LegacyReference.entity == "equipment")
                )
            ).scalars()
        )
    assert {"CLI-00123/EA0012301", "10500/EA0012301"} <= legacy_ids
    revisar = [i for i in report.equipment.to_review if "código repetido" in i.reason]
    assert [(i.row, i.reason) for i in revisar] == [
        (4, "código repetido en Persat: se le asignó EA0012301"),
        (5, "código repetido en Persat: se le asignó EA1050001"),
    ]


# Criterio 6: sin ubicación queda "Sin ubicación" y se informa.
async def test_equipo_sin_ubicacion(schema: None, clientes_xlsx: Path, equipos_xlsx: Path) -> None:
    report = await _import(clientes_xlsx, equipos_xlsx)

    assert (await _equipment_by_code())["EA1064202"].location_note == "Sin ubicación"
    assert Issue(3, "equipo EA1064202 (cliente 10642)", "sin ubicación") in (
        report.equipment.to_review
    )


# ---------- Línea de comandos ----------


async def test_linea_de_comandos_por_defecto_es_una_prueba(
    schema: None, clientes_xlsx: Path
) -> None:
    report = await _import(clientes_xlsx, apply=False)
    output = cli.format_report(report, clients=True, equipment=False)

    assert output.startswith("MODO PRUEBA: no se guardó nada.")
    assert "Se crearían: 3" in output
    assert "fila 7, cliente CLP-9999: registro de prueba" in output
    # El informe no muestra nombres.
    assert "Hotel Ficticio" not in output
