"""Importa desde la exportación de Persat: clientes y equipos (E11-01, E11-02) y el
historial de órdenes (E11-03).

Por defecto es una prueba: informa qué haría y no guarda nada. Con --aplicar, guarda en un
lote que se puede deshacer (E11-05). Se puede repetir: lo ya importado no se vuelve a crear.
Con --informe, escribe además un CSV con cada problema y una sugerencia (E11-04).

Uso:
    python -m app.persat_import --clientes clientes.xlsx --equipos equipos.xlsx \\
        --ordenes carpeta_de_ordenes [--informe problemas.csv] [--aplicar --por "Nombre"]
    python -m app.persat_import --lotes
    python -m app.persat_import --deshacer <id del lote>

Los archivos de Persat tienen datos reales: nunca dentro del repo (persat-export/ está
ignorado). El informe muestra número de fila, de cliente y de orden, sin nombres ni
contactos.
"""

import argparse
import asyncio
import csv
import sys
import uuid
from pathlib import Path

from app.db.session import SessionLocal, engine
from app.services import persat_batches
from app.services.persat_common import Issue, PersatFileError
from app.services.persat_import import (
    CLIENT_HEADERS,
    EQUIPMENT_HEADERS,
    EntityReport,
    ImportReport,
    import_persat,
    read_rows,
)
from app.services.persat_orders import OrdersReport, read_order_files

# Qué hacer con cada problema del informe (E11-04): por palabra clave del motivo.
_SUGGESTIONS = (
    ("registro interno", "No se migra: es de uso interno de Persat."),
    ("registro de prueba", "No se migra: es un registro de prueba."),
    ("repetid", "Corregir el número en Persat o dejar uno solo antes de exportar."),
    ("sin dirección", "Cargar la dirección del domicilio en el sistema."),
    ("sin ubicación", "Cargar la ubicación del equipo en el sistema."),
    ("cliente no", "Importar primero el cliente o corregir su número en Persat."),
    ("domicilio", "Darle un domicilio activo al cliente."),
    ("fecha", "Corregir la fecha en Persat."),
    ("tipo de trabajo", "Revisar si el tipo de trabajo se usa: queda desactivado."),
    ("caracteres", "Acortar el texto en Persat."),
)


async def _run(
    clients: Path | None,
    equipment: Path | None,
    orders: Path | None,
    apply: bool,
    run_by: str,
) -> ImportReport:
    client_rows = read_rows(clients, CLIENT_HEADERS) if clients else None
    equipment_rows = read_rows(equipment, EQUIPMENT_HEADERS) if equipment else None
    order_rows = read_order_files(orders) if orders else None
    try:
        async with SessionLocal() as session:
            return await import_persat(
                session,
                clients=client_rows,
                equipment=equipment_rows,
                orders=order_rows,
                apply=apply,
                run_by=run_by,
            )
    finally:
        await engine.dispose()


def format_report(
    report: ImportReport, *, clients: bool, equipment: bool, orders: bool = False
) -> str:
    verb = "Se crearon" if report.applied else "Se crearían"
    lines = []
    if not report.applied:
        lines += ["MODO PRUEBA: no se guardó nada. Para guardar: --aplicar.", ""]
    if clients:
        lines += _section("Clientes", report.clients, verb)
        if report.probable_duplicates:
            lines.append("  Posibles sedes de un mismo cliente (para unificar a mano):")
            lines += [f"    {', '.join(group)}" for group in report.probable_duplicates]
            lines.append("")
    if equipment:
        lines += _section("Equipos", report.equipment, verb)
    if orders:
        lines += _orders_section(report.orders, verb)
    if report.batch_id is not None:
        lines.append(f"Lote {report.batch_id}. Para deshacerlo: --deshacer {report.batch_id}")
    return "\n".join(lines)


def _section(title: str, entity: EntityReport, verb: str) -> list[str]:
    lines = [
        f"{title}:",
        f"  {verb}: {entity.created}",
        f"  Ya importados antes: {entity.existing}",
        f"  No se migran: {len(entity.skipped)}",
        f"  Con errores (no se importan): {len(entity.errors)}",
        f"  Para revisar: {len(entity.to_review)}",
    ]
    for label, issues in (
        ("No se migran", entity.skipped),
        ("Errores", entity.errors),
        ("Para revisar", entity.to_review),
    ):
        if issues:
            lines.append(f"  {label}:")
            lines += [f"    fila {i.row}, {i.ref}: {i.reason}" for i in issues]
    lines.append("")
    return lines


def _orders_section(orders: OrdersReport, verb: str) -> list[str]:
    lines = [
        "Órdenes (historial):",
        f"  {verb}: {orders.created}, de {len(orders.clients)} clientes",
        f"  Con equipo: {orders.with_equipment}; "
        f"sin equipo: {orders.created - orders.with_equipment}",
        f"  Ya importadas antes: {orders.existing}",
        f"  Con errores (no se importan): {len(orders.errors)}",
    ]
    lines += [f"    {name}: {count}" for name, count in sorted(orders.by_work_type.items())]
    for label, issues in (("Errores", orders.errors), ("Para revisar", orders.to_review)):
        if issues:
            lines.append(f"  {label}:")
            lines += [f"    fila {i.row}, {i.ref}: {i.reason}" for i in issues]
    lines.append("")
    return lines


def suggestion(reason: str) -> str:
    for keyword, text in _SUGGESTIONS:
        if keyword in reason:
            return text
    return "Revisar el registro en Persat."


def write_quality_report(report: ImportReport, path: Path) -> int:
    """CSV con cada problema, su fila y una sugerencia, y los posibles duplicados (E11-04).
    Solo números de fila, cliente, equipo u orden: nada que no esté en los archivos."""
    rows: list[tuple[str, str, Issue]] = []
    for entity, entity_report in (("cliente", report.clients), ("equipo", report.equipment)):
        for kind, issues in (
            ("no se migra", entity_report.skipped),
            ("error", entity_report.errors),
            ("para revisar", entity_report.to_review),
        ):
            rows += [(entity, kind, issue) for issue in issues]
    rows += [("orden", "error", issue) for issue in report.orders.errors]
    rows += [("orden", "para revisar", issue) for issue in report.orders.to_review]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["entidad", "tipo", "fila", "referencia", "problema", "sugerencia"])
        for entity, kind, issue in rows:
            writer.writerow(
                [entity, kind, issue.row, issue.ref, issue.reason, suggestion(issue.reason)]
            )
        for group in report.probable_duplicates:
            writer.writerow(
                [
                    "cliente",
                    "posible duplicado",
                    "",
                    ", ".join(group),
                    "mismo nombre en varios clientes",
                    "Unificarlos con E03-08 si son el mismo cliente (mismo CUIT).",
                ]
            )
    return len(rows) + len(report.probable_duplicates)


async def _batches() -> str:
    try:
        async with SessionLocal() as session:
            batches = await persat_batches.list_batches(session)
    finally:
        await engine.dispose()
    if not batches:
        return "No hay lotes de importación."
    return "\n".join(
        f"{b.id}  {b.started_at:%d/%m/%Y %H:%M}  {b.run_by}  {b.summary}"
        + ("  (deshecho)" if b.undone_at else "")
        for b in batches
    )


async def _undo(batch_id: uuid.UUID) -> str:
    try:
        async with SessionLocal() as session:
            batch = await persat_batches.undo_batch(session, batch_id)
    finally:
        await engine.dispose()
    return f"Lote {batch.id} deshecho ({batch.summary})."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Importa clientes, equipos y órdenes de Persat.")
    parser.add_argument("--clientes", type=Path, help="exportación de clientes (.xlsx)")
    parser.add_argument("--equipos", type=Path, help="exportación de equipos (.xlsx)")
    parser.add_argument("--ordenes", type=Path, help="carpeta con los .xls de órdenes")
    parser.add_argument("--informe", type=Path, help="CSV con los problemas y sugerencias")
    parser.add_argument("--aplicar", action="store_true", help="guardar (sin esto, es una prueba)")
    parser.add_argument("--por", default="", help="quién corre la importación (queda en el lote)")
    parser.add_argument("--lotes", action="store_true", help="listar los lotes importados")
    parser.add_argument("--deshacer", type=uuid.UUID, help="deshacer un lote entero")
    args = parser.parse_args(argv)

    if args.lotes:
        print(asyncio.run(_batches()))
        return 0
    if args.deshacer:
        try:
            print(asyncio.run(_undo(args.deshacer)))
        except persat_batches.BatchNotFoundError:
            print("No existe ese lote.", file=sys.stderr)
            return 1
        except persat_batches.BatchAlreadyUndoneError:
            print("Ese lote ya estaba deshecho.", file=sys.stderr)
            return 1
        except persat_batches.BatchInUseError as error:
            print(f"No se deshace: {error.message}", file=sys.stderr)
            return 1
        return 0
    if not (args.clientes or args.equipos or args.ordenes):
        parser.error("indicá --clientes, --equipos, --ordenes, --lotes o --deshacer")

    try:
        report = asyncio.run(
            _run(args.clientes, args.equipos, args.ordenes, args.aplicar, args.por)
        )
    except PersatFileError as error:
        print(error.message, file=sys.stderr)
        return 1
    print(
        format_report(
            report,
            clients=bool(args.clientes),
            equipment=bool(args.equipos),
            orders=bool(args.ordenes),
        )
    )
    if args.informe:
        count = write_quality_report(report, args.informe)
        print(f"Informe de calidad: {count} filas en {args.informe}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
