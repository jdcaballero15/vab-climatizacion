import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.conftest import TEST_DATABASE_URL

BACKEND_DIR = Path(__file__).resolve().parent.parent

# Criterio 2: alembic upgrade head crea el esquema inicial sin errores y
# alembic downgrade base lo deshace.


def _alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    return cfg


def _reset_database() -> None:
    """Deja ot_test sin esquema ni control de versiones, para aislar el test."""

    async def reset() -> None:
        engine = create_async_engine(TEST_DATABASE_URL)
        async with engine.begin() as conn:
            await conn.execute(text("DROP TABLE IF EXISTS app_user CASCADE"))
            await conn.execute(text("DROP TYPE IF EXISTS user_role"))
            await conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
        await engine.dispose()

    asyncio.run(reset())


def _current_revision() -> str | None:
    async def query() -> str | None:
        engine = create_async_engine(TEST_DATABASE_URL)
        try:
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT version_num FROM alembic_version"))
                row = result.first()
                return row[0] if row else None
        except Exception:
            return None
        finally:
            await engine.dispose()

    return asyncio.run(query())


def test_migrations_upgrade_and_downgrade_are_reversible() -> None:
    cfg = _alembic_config()
    _reset_database()

    head = ScriptDirectory.from_config(cfg).get_current_head()

    command.upgrade(cfg, "head")
    assert _current_revision() == head

    command.downgrade(cfg, "base")
    assert _current_revision() is None
