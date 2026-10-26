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
            await conn.execute(text("DROP TABLE IF EXISTS client_contact CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS client CASCADE"))
            await conn.execute(text("DROP TYPE IF EXISTS client_segment"))
            await conn.execute(text("DROP TYPE IF EXISTS tax_condition"))
            await conn.execute(text("DROP TABLE IF EXISTS repair CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS failure CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS equipment_type CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS task CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS work_type CASCADE"))
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


def _names(query_sql: str) -> list[str]:
    async def query() -> list[str]:
        engine = create_async_engine(TEST_DATABASE_URL)
        try:
            async with engine.connect() as conn:
                result = await conn.execute(text(query_sql))
                return sorted(row[0] for row in result)
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


# E02-01, criterio 9: una base recién migrada trae los seis tipos de trabajo iniciales.
def test_migracion_carga_los_tipos_de_trabajo_iniciales() -> None:
    cfg = _alembic_config()
    _reset_database()

    command.upgrade(cfg, "head")
    try:
        assert _names("SELECT name FROM work_type WHERE is_active") == [
            "Devolución",
            "Instalación",
            "Relevamiento",
            "Reparación",
            "Retiro",
            "Service",
        ]
    finally:
        command.downgrade(cfg, "base")


# E02-02, criterio 6: una base recién migrada trae los seis tipos de equipo iniciales.
def test_migracion_carga_los_tipos_de_equipo_iniciales() -> None:
    cfg = _alembic_config()
    _reset_database()

    command.upgrade(cfg, "head")
    try:
        assert _names("SELECT name FROM equipment_type WHERE is_active") == [
            "Aire acondicionado",
            "Cámara de frío",
            "Freezer",
            "Heladera comercial",
            "Heladera familiar",
            "Otros",
        ]
    finally:
        command.downgrade(cfg, "base")


# E02-03, criterio 9: una base recién migrada trae las 3 fallas genéricas del cliente.
def test_migracion_carga_las_fallas_iniciales() -> None:
    cfg = _alembic_config()
    _reset_database()

    command.upgrade(cfg, "head")
    try:
        assert _names("SELECT name FROM failure WHERE is_active AND equipment_type_id IS NULL") == [
            "Falla del sistema de gas",
            "Falla eléctrica o mecánica",
            "Revisión y limpieza",
        ]
        assert _names("SELECT name FROM failure WHERE equipment_type_id IS NOT NULL") == []
    finally:
        command.downgrade(cfg, "base")


# E02-04, criterio 9: una base recién migrada trae las reparaciones del cliente, cada una con
# su falla y su tipo (o genérica); las de varios tipos, una vez por tipo; sin "Otros".
REPAIR_SCOPES_SQL = """
    SELECT r.name || ' | ' || f.name || ' | ' || coalesce(t.name, 'genérica')
    FROM repair r
    JOIN failure f ON f.id = r.failure_id
    LEFT JOIN equipment_type t ON t.id = r.equipment_type_id
    WHERE r.is_active
"""


def test_migracion_carga_las_reparaciones_iniciales() -> None:
    cfg = _alembic_config()
    _reset_database()

    command.upgrade(cfg, "head")
    try:
        filas = _names(REPAIR_SCOPES_SQL)
        assert len(filas) == 48
        assert len({fila.split(" | ")[0] for fila in filas}) == 36
        assert not any(fila.startswith("Otros") for fila in filas)
        gas = "Falla del sistema de gas"
        assert f"Cambio de válvula inversora | {gas} | Aire acondicionado" in filas
        assert [f for f in filas if f.startswith("Cambio de capilar")] == [
            f"Cambio de capilar | {gas} | Cámara de frío",
            f"Cambio de capilar | {gas} | Freezer",
            f"Cambio de capilar | {gas} | Heladera comercial",
            f"Cambio de capilar | {gas} | Heladera familiar",
        ]
        assert "Cambio de capacitor | Falla eléctrica o mecánica | genérica" in filas
        assert "Limpieza de difusores | Revisión y limpieza | Aire acondicionado" in filas
    finally:
        command.downgrade(cfg, "base")


def test_downgrade_de_los_datos_iniciales_deja_los_catalogos_vacios() -> None:
    cfg = _alembic_config()
    _reset_database()

    command.upgrade(cfg, "head")
    # Hasta antes de la carga inicial, aunque después se sumen migraciones.
    command.downgrade(cfg, "154f870b70dc")
    try:
        assert _names("SELECT name FROM repair") == []
        assert _names("SELECT name FROM failure") == []
    finally:
        command.downgrade(cfg, "base")


# E03-01: el downgrade de clientes también borra sus tipos enum, para poder volver a subir.
def test_downgrade_de_clientes_borra_sus_tipos() -> None:
    cfg = _alembic_config()
    _reset_database()

    command.upgrade(cfg, "head")
    command.downgrade(cfg, "7a8a9559f9b4")
    try:
        assert (
            _names(
                "SELECT typname FROM pg_type WHERE typname IN ('client_segment', 'tax_condition')"
            )
            == []
        )
    finally:
        command.downgrade(cfg, "base")
