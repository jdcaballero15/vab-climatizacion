"""Importa clientes y equipos desde la exportación de Persat (E11-01, E11-02).

Por defecto es una prueba: informa qué haría y no guarda nada. Con --aplicar, guarda.
Se puede repetir: lo ya importado no se vuelve a crear.

Uso:
    python -m app.persat_import --clientes clientes.xlsx --equipos equipos.xlsx [--aplicar]

Los archivos de Persat tienen datos reales: nunca dentro del repo (persat-export/ está
ignorado). El informe muestra número de fila y de cliente, sin nombres ni contactos.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from app.db.session import SessionLocal, engine
from app.services.persat_import import (
    CLIENT_HEADERS,
    EQUIPMENT_HEADERS,
    EntityReport,
    ImportReport,
    PersatFileError,
    import_persat,
    read_rows,
)


async def _run(clients: Path | None, equipment: Path | None, apply: bool) -> ImportReport:
    client_rows = read_rows(clients, CLIENT_HEADERS) if clients else None
    equipment_rows = read_rows(equipment, EQUIPMENT_HEADERS) if equipment else None
    try:
        async with SessionLocal() as session:
            return await import_persat(
                session, clients=client_rows, equipment=equipment_rows, apply=apply
            )
    finally:
        await engine.dispose()


def format_report(report: ImportReport, *, clients: bool, equipment: bool) -> str:
    verb = "Se crearon" if report.applied else "Se crearían"
    lines = []
    if not report.applied:
        lines += ["MODO PRUEBA: no se guardó nada. Para guardar: --aplicar.", ""]
    if clients:
        lines += _section("Clientes", report.clients, verb)
    if equipment:
        lines += _section("Equipos", report.equipment, verb)
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Importa clientes y equipos de Persat.")
    parser.add_argument("--clientes", type=Path, help="exportación de clientes (.xlsx)")
    parser.add_argument("--equipos", type=Path, help="exportación de equipos (.xlsx)")
    parser.add_argument("--aplicar", action="store_true", help="guardar (sin esto, es una prueba)")
    args = parser.parse_args(argv)
    if not args.clientes and not args.equipos:
        parser.error("indicá --clientes, --equipos o los dos")

    try:
        report = asyncio.run(_run(args.clientes, args.equipos, args.aplicar))
    except PersatFileError as error:
        print(error.message, file=sys.stderr)
        return 1
    print(format_report(report, clients=bool(args.clientes), equipment=bool(args.equipos)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
