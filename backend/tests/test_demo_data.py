from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import text

from app.db.models.refresh_token import RefreshToken
from app.db.models.user import User, UserRole
from app.db.repositories.user import UserRepository
from app.db.session import SessionLocal, engine
from app.services.auth import authenticate
from app.services.demo_data import (
    DEMO_EMAIL_DOMAIN,
    DEMO_FIRST_NAMES,
    DEMO_LAST_NAMES,
    DatabaseNotEmptyError,
    DemoDataRefusedError,
    ensure_can_run,
    generate_demo_data,
)
from tests.factories import make_user

PASSWORD = "Secreta123"


async def _create_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(
            User.metadata.create_all, tables=[User.__table__, RefreshToken.__table__]
        )


async def _drop_schema() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.drop_all, tables=[RefreshToken.__table__, User.__table__])
        await conn.execute(text("DROP TYPE IF EXISTS user_role"))


@pytest.fixture
async def schema() -> AsyncGenerator[None, None]:
    await _create_schema()
    yield
    await _drop_schema()


async def _generate(seed: int = 1) -> list[tuple[str, str, UserRole]]:
    async with SessionLocal() as session:
        await generate_demo_data(session, password=PASSWORD, seed=seed)
    async with SessionLocal() as session:
        users = await UserRepository(session).list()
    return sorted((u.email, u.full_name, u.role) for u in users)


# Criterio 1: sobre una base vacía crea usuarios de cada rol, que pueden iniciar sesión.
async def test_crea_usuarios_de_cada_rol(schema: None) -> None:
    generated = await _generate()

    roles = [role for _, _, role in generated]
    assert roles.count(UserRole.admin) == 1
    assert roles.count(UserRole.owner) == 1
    assert roles.count(UserRole.technician) == 4

    async with SessionLocal() as session:
        for email, _, _ in generated:
            assert await authenticate(session, email, PASSWORD) is not None


# Criterio 2: solo datos inventados (dominio de prueba y nombres de las listas ficticias).
async def test_los_datos_son_ficticios(schema: None) -> None:
    generated = await _generate()

    for email, full_name, _ in generated:
        assert email.endswith(f"@{DEMO_EMAIL_DOMAIN}")
        first, last = full_name.split(" ")
        assert first in DEMO_FIRST_NAMES
        assert last in DEMO_LAST_NAMES


async def test_no_repite_nombres(schema: None) -> None:
    generated = await _generate()

    full_names = [full_name for _, full_name, _ in generated]
    assert len(set(full_names)) == len(full_names)


# Criterio 3: con la misma semilla, dos corridas generan exactamente lo mismo.
async def test_es_repetible_con_la_misma_semilla() -> None:
    await _create_schema()
    try:
        primera = await _generate(seed=42)
    finally:
        await _drop_schema()

    await _create_schema()
    try:
        segunda = await _generate(seed=42)
    finally:
        await _drop_schema()

    assert primera == segunda


# Criterio 4: si la base ya tiene datos, no escribe nada.
async def test_no_escribe_si_la_base_tiene_datos(schema: None) -> None:
    async with SessionLocal() as session:
        session.add(make_user(email="existente@ot-demo.com", is_active=False))
        await session.commit()

    async with SessionLocal() as session:
        with pytest.raises(DatabaseNotEmptyError):
            await generate_demo_data(session, password=PASSWORD, seed=1)

    async with SessionLocal() as session:
        users = await UserRepository(session).list(include_deleted=True)
    assert [u.email for u in users] == ["existente@ot-demo.com"]


# Criterio 5: se niega a correr en producción o sin contraseña definida.
@pytest.mark.parametrize(
    ("app_env", "password"),
    [("production", PASSWORD), ("local", None), ("local", ""), ("local", "corta")],
)
def test_se_niega_a_correr(app_env: str, password: str | None) -> None:
    with pytest.raises(DemoDataRefusedError):
        ensure_can_run(app_env=app_env, password=password)


def test_permite_correr_en_local_con_contrasena() -> None:
    assert ensure_can_run(app_env="local", password=PASSWORD) == PASSWORD
