"""Recuperar el acceso desde la consola cuando nadie de administración puede entrar."""

import asyncio
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import text

from app import reset_password as cli
from app.db.models.refresh_token import RefreshToken
from app.db.models.user import User, UserRole
from app.db.session import SessionLocal, engine
from app.services.auth import authenticate
from tests.factories import make_user

TABLES = [User.__table__, RefreshToken.__table__]


@pytest.fixture
async def schema() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.create_all, tables=TABLES)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.drop_all, tables=TABLES)
        await conn.execute(text("DROP TYPE IF EXISTS user_role"))


async def test_genera_una_temporal_que_obliga_a_cambiarla(
    schema: None, capsys: pytest.CaptureFixture[str]
) -> None:
    async with SessionLocal() as session:
        session.add(make_user(email="admin@ot-demo.com", role=UserRole.admin))
        await session.commit()
    # El comando corre su propio loop: se sueltan antes las conexiones de este.
    await engine.dispose()

    code = await asyncio.to_thread(cli.main, ["--email", "admin@ot-demo.com"])

    assert code == 0
    temporary = capsys.readouterr().out.split("Contraseña temporal: ")[1].split()[0]
    async with SessionLocal() as session:
        user = await authenticate(session, "admin@ot-demo.com", temporary)
    assert user is not None
    assert user.must_change_password
    assert user.password_reset_at is not None
    assert user.password_reset_by is None


async def test_correo_inexistente_no_cambia_nada(
    schema: None, capsys: pytest.CaptureFixture[str]
) -> None:
    await engine.dispose()

    code = await asyncio.to_thread(cli.main, ["--email", "nadie@ot-demo.com"])

    assert code == 1
    assert "No hay un usuario activo con ese correo" in capsys.readouterr().err
