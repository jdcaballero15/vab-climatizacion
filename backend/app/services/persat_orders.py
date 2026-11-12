"""Historial de trabajos de Persat (E11-03).

Cada formulario de Persat se exporta como un `.xls` que en realidad es una tabla HTML,
con tablas anidadas en algunas celdas (datos del equipo, materiales, checklist). Se lee
con el parser de la biblioteca estándar. Reglas en docs/domain/migracion-persat.md.

Las órdenes importadas quedan con source = persat: se ven en el historial del cliente y
del equipo, marcadas como importadas, y no entran en el panel ni en las estadísticas.
"""

import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dates import BUSINESS_TZ
from app.db.models.catalog import WorkType
from app.db.models.client import ClientSite
from app.db.models.legacy_reference import LegacyReference
from app.db.models.work_order import WorkOrder, WorkOrderEvent
from app.domain import persat
from app.domain.work_order import OrderSource, OrderStatus, WorkOrderEventType
from app.services.persat_common import SOURCE, Issue, PersatFileError, reference

ORDER_ENTITY = "work_order"
_COMMON_HEADERS = ("#Num.", "Estado", "Fecha", "Nro. de Cliente", "Etiquetas", "Tecnico")
# Las primeras columnas son las comunes; los campos del formulario empiezan después de
# "Tecnico" (hay dos "Tipo": el del cliente y el del formulario).
_FORM_START = len(
    (
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
    )
)


@dataclass
class Cell:
    text: str
    # Tablas anidadas: cada una, filas de textos.
    tables: list[list[list[str]]] = field(default_factory=list)


@dataclass(frozen=True)
class OrderRow:
    form: str
    row: int
    headers: tuple[str, ...]
    cells: tuple[Cell, ...]

    def value(self, header: str) -> str:
        index = self.headers.index(header)
        return self.cells[index].text if index < len(self.cells) else ""


@dataclass
class OrdersReport:
    created: int = 0
    existing: int = 0
    with_equipment: int = 0
    clients: set[str] = field(default_factory=set)
    by_work_type: Counter[str] = field(default_factory=Counter)
    errors: list[Issue] = field(default_factory=list)
    to_review: list[Issue] = field(default_factory=list)


class _TableParser(HTMLParser):
    """La tabla de primer nivel: encabezados y filas; las anidadas quedan en su celda."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.headers: list[str] = []
        self.rows: list[list[Cell]] = []
        self._in_head = False
        self._row: list[Cell] | None = None
        self._cell: Cell | None = None
        self._text: list[str] = []
        self._nested: list[list[list[str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self.depth += 1
            if self.depth > 1:
                self._nested.append([])
        elif self.depth == 1:
            if tag == "thead":
                self._in_head = True
            elif tag == "tr":
                self._row = []
            elif tag in ("td", "th"):
                self._cell = Cell("")
                self._text = []
        elif self._nested:
            if tag == "tr":
                self._nested[-1].append([])
            elif tag in ("td", "th") and self._nested[-1]:
                self._nested[-1][-1].append("")

    def handle_endtag(self, tag: str) -> None:
        if tag == "table":
            if self.depth > 1 and self._nested:
                table = self._nested.pop()
                if self._cell is not None:
                    self._cell.tables.append([[persat.text(v) for v in row] for row in table])
            self.depth -= 1
        elif self.depth == 1:
            if tag == "thead":
                self._in_head = False
            elif tag in ("td", "th") and self._cell is not None and self._row is not None:
                self._cell.text = persat.text("".join(self._text))
                self._row.append(self._cell)
                self._cell = None
            elif tag == "tr" and self._row is not None:
                if self._in_head or not self.headers:
                    self.headers = [cell.text for cell in self._row]
                else:
                    self.rows.append(self._row)
                self._row = None

    def handle_data(self, data: str) -> None:
        if self._cell is None:
            return
        if self.depth == 1:
            self._text.append(data)
        elif self._nested and self._nested[-1] and self._nested[-1][-1]:
            self._nested[-1][-1][-1] += data


def read_order_files(folder: Path) -> list[OrderRow]:
    """Las órdenes de todos los formularios de la carpeta, en orden de archivo y fila."""
    if not folder.is_dir():
        raise PersatFileError(f"{folder} no es una carpeta con los archivos de órdenes.")
    rows: list[OrderRow] = []
    for path in sorted(folder.glob("*.xls")):
        form = path.stem.lower()
        if persat.order_work_type(form) is None:
            raise PersatFileError(f"No se reconoce el formulario {path.name}.")
        parser = _TableParser()
        try:
            parser.feed(path.read_text(encoding="utf-8", errors="replace"))
        except OSError as exc:
            raise PersatFileError(f"No se pudo leer {path.name}: {exc}") from None
        missing = [name for name in _COMMON_HEADERS if name not in parser.headers]
        if missing:
            raise PersatFileError(f"A {path.name} le faltan las columnas: {', '.join(missing)}.")
        headers = tuple(parser.headers)
        rows.extend(
            OrderRow(form, number, headers, tuple(cells))
            for number, cells in enumerate(parser.rows, start=2)
        )
    return rows


async def import_orders(session: AsyncSession, rows: list[OrderRow], report: OrdersReport) -> None:
    """Crea las órdenes nuevas en la transacción en curso; no confirma."""
    work_types: dict[str, WorkType] = {}
    seen: set[str] = set()
    for order_row in rows:
        number = order_row.value("#Num.")
        ref = f"{order_row.form} orden {number or 'sin número'}"
        if not number or number in seen:
            report.errors.append(
                Issue(order_row.row, ref, "sin número" if not number else "repetida")
            )
            continue
        seen.add(number)
        if await _reference_id(session, ORDER_ENTITY, number) is not None:
            report.existing += 1
            continue
        client_number = persat.client_number(order_row.value("Nro. de Cliente"))
        client_id = await _reference_id(session, "client", client_number)
        if client_id is None:
            report.errors.append(Issue(order_row.row, ref, "el cliente no está importado"))
            continue
        site = await session.scalar(
            select(ClientSite)
            .where(ClientSite.client_id == client_id, ClientSite.deleted_at.is_(None))
            .order_by(ClientSite.created_at)
            .limit(1)
        )
        date = persat.order_date(order_row.value("Fecha"))
        if site is None or date is None:
            reason = "el cliente no tiene domicilio" if site is None else "fecha inválida"
            report.errors.append(Issue(order_row.row, ref, reason))
            continue
        work_type_name = persat.order_work_type(order_row.form) or "Reparación"
        work_type = work_types.get(work_type_name) or await _work_type(
            session, work_type_name, report
        )
        work_types[work_type_name] = work_type
        equipment_id = await _equipment(session, order_row, client_number)
        raw_status = order_row.value("Estado")
        status = (
            OrderStatus.cancelled if raw_status == persat.CANCELLED_STATUS else OrderStatus.done
        )
        order = WorkOrder(
            source=OrderSource.persat,
            status=status,
            client_id=client_id,
            client_site_id=site.id,
            work_type_id=work_type.id,
            equipment_id=equipment_id,
            description=_description(order_row, number, raw_status),
        )
        session.add(order)
        await session.flush()
        year, month, day, hour, minute = date
        session.add(
            WorkOrderEvent(
                work_order_id=order.id,
                event_type=WorkOrderEventType.created,
                to_status=status,
                occurred_at=datetime(year, month, day, hour, minute, tzinfo=BUSINESS_TZ),
                note=f"Importada de Persat (N° {number}).",
            )
        )
        session.add(reference(ORDER_ENTITY, order.id, number))
        report.created += 1
        report.clients.add(client_number)
        report.by_work_type[work_type_name] += 1
        if equipment_id is not None:
            report.with_equipment += 1


def _description(order_row: OrderRow, number: str, raw_status: str) -> str:
    """Un texto de solo lectura con lo de Persat: número, estado, cuadrilla, técnicos y el
    detalle (reclamo, observación, trabajo, falla, causal y tareas)."""
    status = persat.PERSAT_STATUSES.get(raw_status, raw_status.lower() or "sin estado")
    lines = [f"Persat N° {number} · {status}"]
    crew = order_row.value("Tecnico")
    technicians = persat.technicians(order_row.value("Etiquetas"))
    if crew:
        lines.append(f"Cuadrilla: {crew}")
    if technicians:
        lines.append(f"Técnicos: {', '.join(technicians)}")
    texts = [
        cell.text
        for header, cell in zip(order_row.headers, order_row.cells, strict=False)
        if persat.is_detail_header(header)
    ]
    body = persat.detail(texts)
    if body:
        lines.append(body)
    return "\n".join(lines)[:2000]


async def _equipment(
    session: AsyncSession, order_row: OrderRow, client_number: str
) -> uuid.UUID | None:
    """El equipo de la celda de datos del equipo (o de "NUMERO DE EQUIPO"), si es un
    código importado. En casi 9 de cada 10 reparaciones dice N/A o está vacío."""
    candidates: list[str] = []
    for index, cell in enumerate(order_row.cells[_FORM_START:], start=_FORM_START):
        header = order_row.headers[index] if index < len(order_row.headers) else ""
        if "NUMERO DE EQUIPO" in header.upper():
            candidates.append(cell.text)
        for table in cell.tables:
            if table and table[0]:
                candidates.append(table[0][0])
    for code in candidates:
        if persat.is_equipment_placeholder(code):
            continue
        # Los equipos se importan con la referencia "cliente/código" (E11-02).
        equipment_id = await _reference_id(session, "equipment", f"{client_number}/{code}")
        if equipment_id is not None:
            return equipment_id
    return None


async def _work_type(session: AsyncSession, name: str, report: OrdersReport) -> WorkType:
    """El tipo de trabajo con ese nombre; si no existe, se crea desactivado (no se ofrece
    para órdenes nuevas) y queda para revisar."""
    work_type = await session.scalar(
        select(WorkType).where(func.lower(WorkType.name) == name.lower())
    )
    if work_type is None:
        work_type = WorkType(name=name, is_active=False)
        session.add(work_type)
        await session.flush()
        report.to_review.append(
            Issue(0, f"tipo de trabajo {name}", "creado desactivado para el historial")
        )
    return work_type


async def _reference_id(session: AsyncSession, entity: str, legacy_id: str) -> uuid.UUID | None:
    return await session.scalar(
        select(LegacyReference.entity_id).where(
            LegacyReference.entity == entity,
            LegacyReference.source == SOURCE,
            LegacyReference.legacy_id == legacy_id,
            LegacyReference.deleted_at.is_(None),
        )
    )
