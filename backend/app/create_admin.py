"""Crea el primer administrador de una instalación nueva.

La contraseña se pide por teclado (no queda en el historial ni en los argumentos). Se
niega si ya hay un administrador: los demás usuarios se crean desde la administración.

Uso:
    python -m app.create_admin --email <correo> --nombre "<nombre y apellido>"
"""

import argparse
import asyncio
import getpass
import sys
from collections.abc import Callable

from pydantic import ValidationError

from app.api.schemas.user import UserCreate
from app.db.models.user import UserRole
from app.db.session import SessionLocal, engine
from app.services.users import (
    AdminAlreadyExistsError,
    EmailAlreadyExistsError,
    create_first_admin,
)


async def _run(data: UserCreate) -> None:
    try:
        async with SessionLocal() as session:
            await create_first_admin(session, data)
    finally:
        await engine.dispose()


def main(
    argv: list[str] | None = None, read_password: Callable[[str], str] = getpass.getpass
) -> int:
    parser = argparse.ArgumentParser(description="Crea el primer administrador.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--nombre", required=True, help="nombre y apellido")
    args = parser.parse_args(argv)

    password = read_password("Contraseña (8 caracteres o más): ")
    if password != read_password("Repetila: "):
        print("Las contraseñas no coinciden: no se creó nada.", file=sys.stderr)
        return 1
    try:
        data = UserCreate(
            full_name=args.nombre, email=args.email, role=UserRole.admin, password=password
        )
    except ValidationError as error:
        campos = ", ".join(str(e["loc"][0]) for e in error.errors())
        print(f"Datos inválidos ({campos}): no se creó nada.", file=sys.stderr)
        return 1
    try:
        asyncio.run(_run(data))
    except AdminAlreadyExistsError:
        print(
            "Ya hay un administrador: creá los usuarios desde la administración.", file=sys.stderr
        )
        return 1
    except EmailAlreadyExistsError:
        print("Ese correo ya tiene un usuario: no se creó nada.", file=sys.stderr)
        return 1
    print(f"Administrador {data.email} creado. Ya puede iniciar sesión.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
