import random

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.models.user import User, UserRole
from app.db.repositories.user import UserRepository

# Datos inventados a propósito: el repositorio es público y nunca lleva datos reales.
# Los apellidos dejan claro que son personas de prueba.
DEMO_EMAIL_DOMAIN = "ot-demo.com"
DEMO_FIRST_NAMES = (
    "Ana",
    "Bruno",
    "Carla",
    "Diego",
    "Elena",
    "Facundo",
    "Gabriela",
    "Hernán",
    "Inés",
    "Julián",
)
DEMO_LAST_NAMES = ("Prueba", "Demo", "Ficticio", "Ensayo", "Muestra", "Ejemplo")

# Correo y rol de cada usuario generado. Los correos son fijos para poder ingresar
# siempre con los mismos; la semilla decide los nombres.
DEMO_USERS = (
    ("admin", UserRole.admin),
    ("direccion", UserRole.owner),
    ("tecnico1", UserRole.technician),
    ("tecnico2", UserRole.technician),
    ("tecnico3", UserRole.technician),
    ("tecnico4", UserRole.technician),
)

MIN_PASSWORD_LENGTH = 8


class DemoDataRefusedError(Exception):
    """El generador no puede correr en este entorno o con esta configuración."""


class DatabaseNotEmptyError(Exception):
    """La base ya tiene datos: el generador no mezcla datos de prueba con datos cargados."""


def ensure_can_run(*, app_env: str, password: str | None) -> str:
    """Devuelve la contraseña a usar o explica por qué el generador no puede correr."""
    if app_env == "production":
        raise DemoDataRefusedError("El generador de datos de prueba no corre en producción.")
    if not password:
        raise DemoDataRefusedError(
            "Falta SEED_PASSWORD: la contraseña de los usuarios de prueba no tiene valor "
            "por defecto porque el repositorio es público."
        )
    if len(password) < MIN_PASSWORD_LENGTH:
        raise DemoDataRefusedError(
            f"SEED_PASSWORD debe tener al menos {MIN_PASSWORD_LENGTH} caracteres."
        )
    return password


async def generate_demo_data(session: AsyncSession, *, password: str, seed: int) -> list[User]:
    """Carga los datos de prueba ficticios en una base vacía. Misma semilla, mismos datos."""
    if await UserRepository(session).list(include_deleted=True):
        raise DatabaseNotEmptyError

    rng = random.Random(seed)  # noqa: S311 (semilla fija a propósito, no es un secreto)
    # Sin repetir: dos usuarios con el mismo nombre se confunden en los listados.
    full_names = rng.sample(
        [f"{first} {last}" for first in DEMO_FIRST_NAMES for last in DEMO_LAST_NAMES],
        len(DEMO_USERS),
    )
    password_hash = hash_password(password)
    users = [
        User(
            email=f"{local_part}@{DEMO_EMAIL_DOMAIN}",
            full_name=full_name,
            role=role,
            password_hash=password_hash,
            is_active=True,
        )
        for (local_part, role), full_name in zip(DEMO_USERS, full_names, strict=True)
    ]
    session.add_all(users)
    await session.commit()
    return users
