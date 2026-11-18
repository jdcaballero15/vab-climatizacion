"""Recupera el acceso de un usuario cuando nadie de administración puede entrar.

Genera una contraseña temporal, cierra las sesiones del usuario y lo obliga a elegir una
nueva al entrar, igual que el botón de Usuarios. La temporal se muestra una sola vez.
Pensado para la consola del servidor (Shell de Render), que llega a la base por adentro.

Uso:
    python -m app.reset_password --email <correo>
"""

import argparse
import asyncio
import sys

from app.db.session import SessionLocal, engine
from app.services.users import UserNotFoundError, reset_password_by_email


async def _run(email: str) -> str:
    try:
        async with SessionLocal() as session:
            return await reset_password_by_email(session, email)
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Genera una contraseña temporal para un usuario.")
    parser.add_argument("--email", required=True)
    args = parser.parse_args(argv)

    try:
        temporary = asyncio.run(_run(args.email.strip()))
    except UserNotFoundError:
        print("No hay un usuario activo con ese correo: no se cambió nada.", file=sys.stderr)
        return 1
    print(f"Contraseña temporal: {temporary}")
    print("Se muestra una sola vez. Al entrar, el sistema pide elegir una nueva.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
