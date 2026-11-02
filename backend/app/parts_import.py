"""Carga inicial de la lista de materiales desde un CSV (E02-05).

Columnas: nombre,unidad (con encabezado). Todos quedan con precio 0: administración los
completa desde la hoja "Materiales y precios". Se puede repetir: lo que ya está no se
vuelve a crear.

Uso:
    python -m app.parts_import materiales.csv

La lista real no se guarda en el repo (es público).
"""

import argparse
import asyncio
import csv
import sys
from pathlib import Path

from app.db.session import SessionLocal, engine
from app.services.parts import ImportResult, import_parts


def read_csv(path: Path) -> list[tuple[str, str]]:
    """Filas (nombre, unidad), sin las que no tienen nombre."""
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None or "nombre" not in reader.fieldnames:
            raise ValueError('El CSV tiene que tener una columna "nombre" (y opcional "unidad").')
        return [
            (row["nombre"].strip(), (row.get("unidad") or "").strip())
            for row in reader
            if (row.get("nombre") or "").strip()
        ]


async def _run(rows: list[tuple[str, str]]) -> ImportResult:
    try:
        async with SessionLocal() as session:
            return await import_parts(session, rows)
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Carga la lista inicial de materiales.")
    parser.add_argument("archivo", type=Path, help="CSV con columnas nombre,unidad")
    args = parser.parse_args(argv)
    try:
        rows = read_csv(args.archivo)
    except (OSError, ValueError) as exc:
        print(f"No se pudo leer el archivo: {exc}", file=sys.stderr)
        return 1
    result = asyncio.run(_run(rows))
    print(f"Materiales creados: {result.created}. Ya estaban: {result.skipped}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
