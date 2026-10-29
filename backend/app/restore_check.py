"""Prueba de restauración de una copia nocturna (E00-07).

Baja la última copia del bucket (o la indicada), la restaura en una base vacía y comprueba
que las migraciones están al día y que cada tabla tiene las mismas filas que al copiarla.
Se corre desde la Shell de la API en Render, con una base temporal como destino: la copia
tiene datos reales y así no sale de Render. Paso a paso en docs/workflow/backups.md.

Uso:
    python -m app.restore_check --destino '<url de una base vacía>' [--clave db/<...>.dump]
"""

import argparse
import asyncio
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from mypy_boto3_s3 import S3Client
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.backup_db import (
    COUNTS_METADATA,
    DUMP_PREFIX,
    MissingToolError,
    backup_client,
    libpq_url,
    postgres_tool,
    table_counts,
)
from app.core.config import async_database_url

BACKEND_DIR = Path(__file__).resolve().parent.parent


class RestoreCheckError(Exception):
    """La restauración no se hizo o no coincide con la copia. El mensaje dice por qué."""


@dataclass(frozen=True)
class RestoreReport:
    key: str
    revision: str
    counts: dict[str, int]


def latest_key(client: S3Client, bucket: str) -> str | None:
    """La copia más nueva: las claves llevan la fecha y hora UTC, así que ordenan solas."""
    keys = [
        item["Key"]
        for page in client.get_paginator("list_objects_v2").paginate(
            Bucket=bucket, Prefix=DUMP_PREFIX
        )
        for item in page.get("Contents", [])
    ]
    return max(keys, default=None)


def _head_revision() -> str:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    head = ScriptDirectory.from_config(config).get_current_head()
    if head is None:
        raise RestoreCheckError("No se encontró la última migración.")
    return head


async def _is_empty(database_url: str) -> bool:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as conn:
            tables = await conn.scalar(
                text("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'")
            )
            return bool(tables == 0)
    finally:
        await engine.dispose()


async def _revision(database_url: str) -> str | None:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as conn:
            revision = await conn.scalar(text("SELECT version_num FROM alembic_version"))
            return str(revision) if revision is not None else None
    finally:
        await engine.dispose()


def run_restore_check(
    target_url: str, client: S3Client, bucket: str, key: str | None = None
) -> RestoreReport:
    target = async_database_url(target_url)
    key = key or latest_key(client, bucket)
    if key is None:
        raise RestoreCheckError("No hay copias en el bucket.")
    # Nunca sobre una base con datos: podría ser la de producción.
    if not asyncio.run(_is_empty(target)):
        raise RestoreCheckError("La base de destino no está vacía: no se restauró nada.")

    expected = json.loads(client.head_object(Bucket=bucket, Key=key)["Metadata"][COUNTS_METADATA])
    with tempfile.TemporaryDirectory() as folder:
        dump = Path(folder) / "ot.dump"
        client.download_file(bucket, key, str(dump))
        try:
            subprocess.run(  # noqa: S603 (argumentos fijos, sin shell)
                [
                    postgres_tool("pg_restore"),
                    "--no-owner",
                    "--no-privileges",
                    "--exit-on-error",
                    "--single-transaction",
                    f"--dbname={libpq_url(target)}",
                    str(dump),
                ],
                check=True,
            )
        except subprocess.CalledProcessError as error:
            raise RestoreCheckError(f"pg_restore falló (código {error.returncode}).") from error

    revision = asyncio.run(_revision(target))
    head = _head_revision()
    if revision != head:
        raise RestoreCheckError(f"La copia está en la migración {revision}, la última es {head}.")
    counts = asyncio.run(table_counts(target))
    differences = [
        f"{table}: {counts.get(table, 0)} en vez de {rows}"
        for table, rows in sorted(expected.items())
        if counts.get(table, 0) != rows
    ]
    if differences:
        raise RestoreCheckError("Las cantidades no coinciden. " + "; ".join(differences))
    return RestoreReport(key=key, revision=revision, counts=counts)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Restaura una copia y la comprueba.")
    parser.add_argument("--destino", required=True, help="dirección de una base vacía")
    parser.add_argument("--clave", help="copia a restaurar (por defecto, la última)")
    args = parser.parse_args(argv)

    client, bucket = backup_client()
    try:
        report = run_restore_check(args.destino, client, bucket, args.clave)
    except (RestoreCheckError, MissingToolError) as error:
        print(error, file=sys.stderr)
        return 1
    print(f"Restauración OK: {report.key}, migración {report.revision}")
    for table, rows in sorted(report.counts.items()):
        print(f"  {table}: {rows}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
