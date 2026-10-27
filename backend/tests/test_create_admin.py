"""Primer administrador de una instalación nueva (E00-05)."""

import asyncio
from collections.abc import AsyncGenerator, Callable

import pytest
from sqlalchemy import text

from app import create_admin as cli
from app.api.schemas.user import UserCreate
from app.db.models.user import User, UserRole
from app.db.repositories.user import UserRepository
from app.db.session import SessionLocal, engine
from app.services.auth import authenticate
from app.services.users import AdminAlreadyExistsError, create_first_admin
from tests.factories import make_user

PASSWORD = "Secreta-123"
ARGS = ["--email", "admin@ot-demo.com", "--nombre", "Admin Ficticia"]


@pytest.fixture
async def schema() -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.create_all, tables=[User.__table__])
    yield
    async with engine.begin() as conn:
        await conn.run_sync(User.metadata.drop_all, tables=[User.__table__])
        await conn.execute(text("DROP TYPE IF EXISTS user_role"))


def _data(role: UserRole = UserRole.technician) -> UserCreate:
    return UserCreate(
        full_name="Admin Ficticia", email="admin@ot-demo.com", role=role, password=PASSWORD
    )


def _passwords(*values: str) -> Callable[[str], str]:
    answers = iter(values)
    return lambda _prompt: next(answers)


async def test_crea_el_primer_administrador_que_puede_entrar(schema: None) -> None:
    async with SessionLocal() as session:
        # El rol lo fija el comando, no lo que venga en los datos.
        user = await create_first_admin(session, _data(UserRole.technician))
    assert user.role == UserRole.admin
    async with SessionLocal() as session:
        assert await authenticate(session, "admin@ot-demo.com", PASSWORD) is not None


async def test_no_crea_otro_si_ya_hay_administrador(schema: None) -> None:
    async with SessionLocal() as session:
        session.add(make_user(email="otra@ot-demo.com", role=UserRole.admin))
        await session.commit()

    async with SessionLocal() as session:
        with pytest.raises(AdminAlreadyExistsError):
            await create_first_admin(session, _data())
    async with SessionLocal() as session:
        assert len(await UserRepository(session).list()) == 1


async def test_linea_de_comandos_crea_el_administrador(
    schema: None, capsys: pytest.CaptureFixture[str]
) -> None:
    # El comando corre su propio loop: se sueltan antes las conexiones de este.
    await engine.dispose()
    code = await asyncio.to_thread(cli.main, ARGS, _passwords(PASSWORD, PASSWORD))

    assert code == 0
    assert "Administrador admin@ot-demo.com creado" in capsys.readouterr().out
    async with SessionLocal() as session:
        [user] = await UserRepository(session).list()
    assert (user.email, user.full_name, user.role) == (
        "admin@ot-demo.com",
        "Admin Ficticia",
        UserRole.admin,
    )


def test_linea_de_comandos_contrasenas_distintas(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(ARGS, _passwords(PASSWORD, "otra-cosa")) == 1
    assert "no coinciden" in capsys.readouterr().err


def test_linea_de_comandos_contrasena_corta(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(ARGS, _passwords("corta", "corta")) == 1
    assert "Datos inválidos (password)" in capsys.readouterr().err
