import asyncio
from pathlib import Path

import pytest
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
            await conn.execute(text("DROP TABLE IF EXISTS work_order_cancellation CASCADE"))
            await conn.execute(text("DROP TYPE IF EXISTS cancel_reason"))
            await conn.execute(text("DROP TABLE IF EXISTS work_order_closure_task CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS work_order_closure_technician CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS work_order_closure CASCADE"))
            await conn.execute(text("DROP TYPE IF EXISTS closure_outcome"))
            await conn.execute(text("DROP TYPE IF EXISTS equipment_condition"))
            await conn.execute(text("DROP TYPE IF EXISTS not_done_reason"))
            await conn.execute(text("DROP TABLE IF EXISTS field_technician CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS crew CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS work_order_assignment CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS work_order_event CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS work_order CASCADE"))
            await conn.execute(text("DROP SEQUENCE IF EXISTS work_order_number_seq"))
            await conn.execute(text("DROP TYPE IF EXISTS order_status"))
            await conn.execute(text("DROP TYPE IF EXISTS order_kind"))
            await conn.execute(text("DROP TYPE IF EXISTS order_source"))
            await conn.execute(text("DROP TYPE IF EXISTS order_channel"))
            await conn.execute(text("DROP TABLE IF EXISTS equipment CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS client_contact CASCADE"))
            await conn.execute(text("DROP TABLE IF EXISTS client_site CASCADE"))
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


def _execute(*statements: str) -> None:
    async def run() -> None:
        engine = create_async_engine(TEST_DATABASE_URL)
        try:
            async with engine.begin() as conn:
                for statement in statements:
                    await conn.execute(text(statement))
        finally:
            await engine.dispose()

    asyncio.run(run())


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


# E03-02: la migración crea client_site y client_contact.client_site_id; el downgrade los quita.
def test_migracion_de_domicilios_es_reversible() -> None:
    cfg = _alembic_config()
    _reset_database()

    columnas = (
        "SELECT table_name || '.' || column_name FROM information_schema.columns "
        "WHERE (table_name = 'client_site' AND column_name = 'address') "
        "OR (table_name = 'client_contact' AND column_name = 'client_site_id')"
    )
    command.upgrade(cfg, "head")
    try:
        assert _names(columnas) == ["client_contact.client_site_id", "client_site.address"]
        command.downgrade(cfg, "db29fc2db829")
        assert _names(columnas) == []
    finally:
        command.downgrade(cfg, "base")


# E03-03: la migración crea equipment y carga el prefijo de código de los seis tipos iniciales.
def test_migracion_de_equipos_carga_los_prefijos() -> None:
    cfg = _alembic_config()
    _reset_database()

    command.upgrade(cfg, "head")
    try:
        assert _names("SELECT name || ' ' || code_prefix FROM equipment_type") == [
            "Aire acondicionado EA",
            "Cámara de frío EC",
            "Freezer EF",
            "Heladera comercial EH",
            "Heladera familiar EH",
            "Otros EO",
        ]
        assert _names("SELECT tablename FROM pg_tables WHERE tablename = 'equipment'") == [
            "equipment"
        ]
        command.downgrade(cfg, "fab1063f3189")
        assert _names("SELECT tablename FROM pg_tables WHERE tablename = 'equipment'") == []
        assert (
            _names(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'equipment_type' AND column_name = 'code_prefix'"
            )
            == []
        )
    finally:
        command.downgrade(cfg, "base")


# E04-01: la migración crea las órdenes, sus eventos, la secuencia y los enums; el downgrade
# los quita para poder volver a subir.
def test_migracion_de_ordenes_es_reversible() -> None:
    cfg = _alembic_config()
    _reset_database()

    objetos = (
        "SELECT tablename FROM pg_tables WHERE tablename IN ('work_order', 'work_order_event') "
        "UNION ALL SELECT sequencename FROM pg_sequences "
        "WHERE sequencename = 'work_order_number_seq' "
        "UNION ALL SELECT typname FROM pg_type "
        "WHERE typname IN ('order_status', 'order_kind', 'order_source')"
    )
    command.upgrade(cfg, "head")
    try:
        assert _names(objetos) == [
            "order_kind",
            "order_source",
            "order_status",
            "work_order",
            "work_order_event",
            "work_order_number_seq",
        ]
        command.downgrade(cfg, "2ecd8961c92f")
        assert _names(objetos) == []
    finally:
        command.downgrade(cfg, "base")


# E04-02: canal y solicitante en work_order; el downgrade los quita junto con el enum.
def test_migracion_de_canal_y_solicitante_es_reversible() -> None:
    cfg = _alembic_config()
    _reset_database()

    objetos = (
        "SELECT column_name FROM information_schema.columns WHERE table_name = 'work_order' "
        "AND column_name IN ('channel', 'requester_name', 'requester_area') "
        "UNION ALL SELECT typname FROM pg_type WHERE typname = 'order_channel'"
    )
    command.upgrade(cfg, "head")
    try:
        assert _names(objetos) == ["channel", "order_channel", "requester_area", "requester_name"]
        command.downgrade(cfg, "9ded0ea86f52")
        assert _names(objetos) == []
    finally:
        command.downgrade(cfg, "base")


# E04-03: asignaciones y requires_approval; el downgrade los quita.
def test_migracion_de_asignaciones_es_reversible() -> None:
    cfg = _alembic_config()
    _reset_database()

    objetos = (
        "SELECT tablename FROM pg_tables WHERE tablename = 'work_order_assignment' "
        "UNION ALL SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'work_order' AND column_name = 'requires_approval'"
    )
    command.upgrade(cfg, "head")
    try:
        assert _names(objetos) == ["requires_approval", "work_order_assignment"]
        command.downgrade(cfg, "b4e1c7a20d93")
        assert _names(objetos) == []
    finally:
        command.downgrade(cfg, "base")


# E02-09: escuadrillas y técnicos; el downgrade los quita.
def test_migracion_de_escuadrillas_es_reversible() -> None:
    cfg = _alembic_config()
    _reset_database()

    tablas = "SELECT tablename FROM pg_tables WHERE tablename IN ('crew', 'field_technician')"
    command.upgrade(cfg, "head")
    try:
        assert _names(tablas) == ["crew", "field_technician"]
        command.downgrade(cfg, "c7d2f4e81a56")
        assert _names(tablas) == []
    finally:
        command.downgrade(cfg, "base")


# E04-03 (D-013): la asignación pasa de técnico a escuadrilla y vuelve; con asignaciones
# cargadas la migración se niega a correr en lugar de borrarlas.
def test_migracion_de_asignacion_a_escuadrilla() -> None:
    cfg = _alembic_config()
    _reset_database()

    columnas = (
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'work_order_assignment' "
        "AND column_name IN ('technician_id', 'crew_id')"
    )
    command.upgrade(cfg, "head")
    try:
        assert _names(columnas) == ["crew_id"]
        command.downgrade(cfg, "d3a9b6e2f417")
        assert _names(columnas) == ["technician_id"]
    finally:
        command.downgrade(cfg, "base")


def test_migracion_a_escuadrilla_no_corre_con_asignaciones() -> None:
    cfg = _alembic_config()
    _reset_database()

    command.upgrade(cfg, "d3a9b6e2f417")
    try:
        _execute(
            "INSERT INTO app_user (id, email, full_name, role, password_hash, is_active) "
            "VALUES ('00000000-0000-0000-0000-000000000001', 't@ot-demo.com', 'T', "
            "'technician', 'x', true)",
            "INSERT INTO client (id, number, name, segment) "
            "VALUES ('00000000-0000-0000-0000-000000000002', '1', 'C', 'unclassified')",
            "INSERT INTO client_site (id, client_id, address, is_active) "
            "VALUES ('00000000-0000-0000-0000-000000000003', "
            "'00000000-0000-0000-0000-000000000002', 'Calle 1', true)",
            "INSERT INTO work_order (id, kind, source, status, client_id, client_site_id, "
            "work_type_id) SELECT '00000000-0000-0000-0000-000000000004', 'on_site', "
            "'manual', 'assigned', '00000000-0000-0000-0000-000000000002', "
            "'00000000-0000-0000-0000-000000000003', id FROM work_type LIMIT 1",
            "INSERT INTO work_order_assignment (id, work_order_id, technician_id, "
            "scheduled_for) VALUES ('00000000-0000-0000-0000-000000000005', "
            "'00000000-0000-0000-0000-000000000004', "
            "'00000000-0000-0000-0000-000000000001', '2099-01-01')",
        )
        with pytest.raises(RuntimeError, match="no se pueden convertir"):
            command.upgrade(cfg, "head")
        assert _current_revision() == "d3a9b6e2f417"
        assert _names("SELECT id::text FROM work_order_assignment") == [
            "00000000-0000-0000-0000-000000000005"
        ]
    finally:
        # El downgrade de c7d2f4e81a56 quita la tabla con sus filas.
        command.downgrade(cfg, "base")


# E02-10, criterio 3: la migración marca Reparación y Service; el downgrade quita la columna.
# Después el cliente pidió que Service no la pida (2026-10-28): otra migración la desmarca.
def test_migracion_marca_los_tipos_que_piden_falla_y_reparacion() -> None:
    cfg = _alembic_config()
    _reset_database()

    columna = (
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'work_type' AND column_name = 'requires_failure_repair'"
    )
    marcados = "SELECT name FROM work_type WHERE requires_failure_repair"
    command.upgrade(cfg, "head")
    try:
        assert _names(marcados) == ["Reparación"]
        command.downgrade(cfg, "f4b8d2a6c731")
        assert _names(marcados) == ["Reparación", "Service"]
        command.downgrade(cfg, "e5b8c1d4a903")
        assert _names(columna) == []
    finally:
        command.downgrade(cfg, "base")


# E05-04, E05-08 y E05-12: tablas y enums del cierre; el downgrade los quita.
def test_migracion_del_cierre_es_reversible() -> None:
    cfg = _alembic_config()
    _reset_database()

    objetos = (
        "SELECT tablename FROM pg_tables WHERE tablename LIKE 'work_order_closure%' "
        "UNION ALL SELECT typname FROM pg_type "
        "WHERE typname IN ('closure_outcome', 'equipment_condition', 'not_done_reason')"
    )
    command.upgrade(cfg, "head")
    try:
        assert _names(objetos) == [
            "closure_outcome",
            "equipment_condition",
            "not_done_reason",
            "work_order_closure",
            "work_order_closure_photo",
            "work_order_closure_task",
            "work_order_closure_technician",
        ]
        command.downgrade(cfg, "a1f3c5e7b902")
        assert _names(objetos) == []
    finally:
        command.downgrade(cfg, "base")


def test_migraciones_de_archivos_y_fotos_son_reversibles() -> None:
    """E00-09 y E05-06: stored_file y las fotos del cierre se crean y se deshacen."""
    cfg = _alembic_config()
    _reset_database()

    tablas = (
        "SELECT tablename FROM pg_tables "
        "WHERE tablename IN ('stored_file', 'work_order_closure_photo')"
    )
    command.upgrade(cfg, "head")
    try:
        assert _names(tablas) == ["stored_file", "work_order_closure_photo"]
        command.downgrade(cfg, "e2a7c9d4f816")
        assert _names(tablas) == ["stored_file"]
        command.downgrade(cfg, "d9f1b3a7c520")
        assert _names(tablas) == []
    finally:
        command.downgrade(cfg, "base")
