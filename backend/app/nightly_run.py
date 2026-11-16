"""Corrida nocturna: copia de la base (E00-07) y después el mantenimiento (E07-04).

Las dos en un solo cron de Render, vab-ot-backup, para pagar uno y no dos. Cada paso corre
aunque el anterior falle (son independientes) y el cron termina con error si falló alguno,
así Render avisa por correo.

Uso:
    python -m app.nightly_run
"""

import sys
import traceback
from collections.abc import Callable

from app import backup_db, maintenance_run

STEPS: tuple[tuple[str, Callable[[], int]], ...] = (
    ("copia", backup_db.main),
    ("mantenimiento", maintenance_run.main),
)


def main() -> int:
    failed = []
    for name, step in STEPS:
        try:
            code = step()
        except Exception:
            traceback.print_exc()
            code = 1
        if code != 0:
            print(f"Falló: {name}.", file=sys.stderr)
            failed.append(name)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
