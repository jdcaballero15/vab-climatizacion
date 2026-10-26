"""Genera datos de prueba ficticios en una base vacía (E11-09).

Uso:
    SEED_PASSWORD=... python -m app.demo_data [--seed N]
"""

import argparse
import asyncio
import sys

from app.core.config import get_settings
from app.db.session import SessionLocal, engine
from app.services.demo_data import (
    DatabaseNotEmptyError,
    DemoDataRefusedError,
    ensure_can_run,
    generate_demo_data,
)

DEFAULT_SEED = 1


async def _run(password: str, seed: int) -> list[str]:
    try:
        async with SessionLocal() as session:
            users = await generate_demo_data(session, password=password, seed=seed)
        return [user.email for user in users]
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Genera datos de prueba ficticios.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="semilla (por defecto 1)")
    args = parser.parse_args(argv)

    settings = get_settings()
    try:
        password = ensure_can_run(app_env=settings.app_env, password=settings.seed_password)
        emails = asyncio.run(_run(password, args.seed))
    except DemoDataRefusedError as error:
        print(error, file=sys.stderr)
        return 1
    except DatabaseNotEmptyError:
        print("La base ya tiene datos: no se generó nada.", file=sys.stderr)
        return 1

    print(f"Usuarios de prueba creados (semilla {args.seed}), con la contraseña de SEED_PASSWORD:")
    for email in emails:
        print(f"  {email}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
