"""Corrida diaria del mantenimiento (E07-04): `python -m app.maintenance_run`.

La corre el cron vab-ot-maintenance de Render todas las mañanas. Genera la orden de cada
visita que vence en la próxima semana; correrla de más no duplica nada.
"""

import asyncio
import logging
import sys

from app.api.schemas.maintenance import MaintenanceRunOut
from app.db.session import SessionLocal, engine
from app.services.maintenance import run_generation


async def _run() -> MaintenanceRunOut:
    try:
        async with SessionLocal() as session:
            return await run_generation(session)
    finally:
        await engine.dispose()


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    result = asyncio.run(_run())
    print(f"Órdenes generadas: {len(result.generated)}. Planes omitidos: {len(result.skipped)}.")
    for item in result.skipped:
        # Sin datos del cliente: solo el código del equipo y el motivo.
        print(f"  Omitido {item.equipment_code or item.plan_id}: {item.reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
