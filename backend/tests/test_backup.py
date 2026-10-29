"""E00-07: copia nocturna de la base y comprobación de la restauración.

Con Postgres y el bucket S3 compatible reales (MinIO en local y en el CI), sin mocks.
Cada test usa bases temporales propias y un bucket propio, así no pisa ot_test.
"""

import asyncio
import json
import os
import subprocess
import sys
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from mypy_boto3_s3 import S3Client
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.backup_db import COUNTS_METADATA, backup_client, libpq_url, run_backup, table_counts
from app.restore_check import RestoreCheckError, latest_key, run_restore_check
from tests.conftest import TEST_DATABASE_URL

BACKEND_DIR = Path(__file__).resolve().parent.parent
NIGHT = datetime(2026, 10, 30, 7, 0, tzinfo=UTC)


def _url_for(database: str) -> str:
    return TEST_DATABASE_URL.rsplit("/", 1)[0] + f"/{database}"


async def _admin_sql(statement: str) -> None:
    engine = create_async_engine(TEST_DATABASE_URL, isolation_level="AUTOCOMMIT")
    try:
        async with engine.connect() as conn:
            await conn.execute(text(statement))
    finally:
        await engine.dispose()


async def _sql(url: str, statement: str, **params: str) -> None:
    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            await conn.execute(text(statement), params)
    finally:
        await engine.dispose()


@pytest.fixture
def make_database() -> Iterator[object]:
    """Crea bases vacías con nombre único y las borra al terminar."""
    created: list[str] = []

    def make() -> str:
        name = f"ot_backup_{uuid.uuid4().hex[:10]}"
        asyncio.run(_admin_sql(f'CREATE DATABASE "{name}"'))
        created.append(name)
        return _url_for(name)

    yield make
    for name in created:
        asyncio.run(_admin_sql(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))


@pytest.fixture
def source(make_database) -> str:  # type: ignore[no-untyped-def]
    """Una base con todas las migraciones y dos usuarios ficticios."""
    url = make_database()
    subprocess.run(  # noqa: S603 (comando fijo del repo)
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env={**os.environ, "DATABASE_URL": url},
        check=True,
        capture_output=True,
    )
    for email in ("copia1@ot-demo.com", "copia2@ot-demo.com"):
        asyncio.run(
            _sql(
                url,
                "INSERT INTO app_user (id, email, full_name, role, password_hash, is_active) "
                "VALUES (gen_random_uuid(), :email, 'Usuario Ficticio', 'technician', "
                "'sin-hash', true)",
                email=email,
            )
        )
    return url


@pytest.fixture
def bucket() -> Iterator[tuple[S3Client, str]]:
    """Un bucket de copias propio del test, vaciado y borrado al terminar."""
    client, _ = backup_client()
    name = f"ot-backups-test-{uuid.uuid4().hex[:8]}"
    client.create_bucket(Bucket=name)
    yield client, name
    for item in client.list_objects_v2(Bucket=name).get("Contents", []):
        client.delete_object(Bucket=name, Key=item["Key"])
    client.delete_bucket(Bucket=name)


def test_libpq_url_vuelve_al_formato_de_pg_dump() -> None:
    assert (
        libpq_url("postgresql+asyncpg://ot:ot@host:5432/ot?ssl=require")
        == "postgresql://ot:ot@host:5432/ot?sslmode=require"
    )
    assert libpq_url("postgresql://ot:ot@host/ot") == "postgresql://ot:ot@host/ot"


# Criterio 1: la copia nocturna queda en el bucket aparte, con las cantidades de la base.
def test_la_copia_sube_un_dump_con_las_cantidades(
    source: str, bucket: tuple[S3Client, str]
) -> None:
    client, name = bucket

    key = run_backup(source, client, name, NIGHT)

    assert key == "db/2026-10-30T0700Z.dump"
    head = client.head_object(Bucket=name, Key=key)
    assert head["ContentLength"] > 0
    counts = json.loads(head["Metadata"][COUNTS_METADATA])
    assert counts["app_user"] == 2
    assert counts == asyncio.run(table_counts(source))


# Criterio 3: restaurada en una base aparte, coincide con la copia y está al día.
def test_restaurar_en_una_base_vacia_coincide_con_la_copia(
    source: str, bucket: tuple[S3Client, str], make_database
) -> None:  # type: ignore[no-untyped-def]
    client, name = bucket
    run_backup(source, client, name, NIGHT)
    target = make_database()

    report = run_restore_check(target, client, name)

    assert report.key == "db/2026-10-30T0700Z.dump"
    assert report.counts["app_user"] == 2
    assert asyncio.run(table_counts(target)) == asyncio.run(table_counts(source))


def test_sin_clave_usa_la_ultima_copia(source: str, bucket: tuple[S3Client, str]) -> None:
    client, name = bucket
    run_backup(source, client, name, NIGHT)
    run_backup(source, client, name, NIGHT.replace(day=31))

    assert latest_key(client, name) == "db/2026-10-31T0700Z.dump"


def test_no_restaura_sobre_una_base_con_tablas(
    source: str, bucket: tuple[S3Client, str], make_database
) -> None:  # type: ignore[no-untyped-def]
    client, name = bucket
    run_backup(source, client, name, NIGHT)
    target = make_database()
    asyncio.run(_sql(target, "CREATE TABLE ajena (id int)"))

    with pytest.raises(RestoreCheckError, match="no está vacía"):
        run_restore_check(target, client, name)

    assert asyncio.run(table_counts(target)) == {"ajena": 0}


def test_avisa_si_las_cantidades_no_coinciden(
    source: str, bucket: tuple[S3Client, str], make_database
) -> None:  # type: ignore[no-untyped-def]
    client, name = bucket
    key = run_backup(source, client, name, NIGHT)
    counts = json.loads(client.head_object(Bucket=name, Key=key)["Metadata"][COUNTS_METADATA])
    counts["app_user"] = 3
    client.copy_object(
        Bucket=name,
        Key=key,
        CopySource={"Bucket": name, "Key": key},
        Metadata={COUNTS_METADATA: json.dumps(counts)},
        MetadataDirective="REPLACE",
    )

    with pytest.raises(RestoreCheckError, match="app_user: 2 en vez de 3"):
        run_restore_check(make_database(), client, name)


def test_sin_copias_avisa(bucket: tuple[S3Client, str], make_database) -> None:  # type: ignore[no-untyped-def]
    client, name = bucket

    with pytest.raises(RestoreCheckError, match="No hay copias"):
        run_restore_check(make_database(), client, name)
