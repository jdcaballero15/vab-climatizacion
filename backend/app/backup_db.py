"""Copia nocturna de la base a un bucket aparte (E00-07).

Corre `pg_dump` en formato propio de Postgres y sube el archivo a `db/<fecha y hora UTC>.dump`.
Guarda en el objeto cuántas filas tenía cada tabla, para que la prueba de restauración
(`python -m app.restore_check`) compruebe que no falta nada. La retención de 30 días es
una regla del bucket, no de este comando (docs/workflow/backups.md).

Uso (lo corre el cron de Render todas las noches):
    python -m app.backup_db
"""

import asyncio
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from mypy_boto3_s3 import S3Client
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.core.storage import s3_client

DUMP_PREFIX = "db/"
COUNTS_METADATA = "table-counts"


class MissingToolError(Exception):
    """Falta pg_dump o pg_restore en la máquina (la imagen del backend los trae)."""


def postgres_tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise MissingToolError(f"No se encontró {name}: hace falta el cliente de Postgres 18.")
    return path


def libpq_url(database_url: str) -> str:
    """La dirección de la base como la entienden pg_dump y pg_restore (sin asyncpg)."""
    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1).replace(
        "ssl=", "sslmode="
    )


async def table_counts(database_url: str) -> dict[str, int]:
    """Filas de cada tabla del esquema public, por nombre."""
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as conn:
            tables = await conn.scalars(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
                    "ORDER BY table_name"
                )
            )
            counts = {}
            for table in tables.all():
                # El nombre sale del catálogo de la base, no de una entrada del usuario.
                result = await conn.scalar(text(f'SELECT count(*) FROM "{table}"'))  # noqa: S608
                counts[table] = int(result or 0)
            return counts
    finally:
        await engine.dispose()


def backup_client() -> tuple[S3Client, str]:
    settings = get_settings()
    client = s3_client(
        settings.backup_s3_endpoint_url,
        settings.backup_s3_access_key,
        settings.backup_s3_secret_key,
        settings.backup_s3_region,
    )
    return client, settings.backup_s3_bucket


def run_backup(database_url: str, client: S3Client, bucket: str, now: datetime) -> str:
    """Copia la base al bucket y devuelve la clave del objeto."""
    key = f"{DUMP_PREFIX}{now.astimezone(UTC):%Y-%m-%dT%H%MZ}.dump"
    counts = asyncio.run(table_counts(database_url))
    with tempfile.TemporaryDirectory() as folder:
        dump = Path(folder) / "ot.dump"
        subprocess.run(  # noqa: S603 (argumentos fijos, sin shell)
            [
                postgres_tool("pg_dump"),
                "--format=custom",
                "--no-owner",
                "--no-privileges",
                f"--file={dump}",
                f"--dbname={libpq_url(database_url)}",
            ],
            check=True,
        )
        client.upload_file(
            str(dump),
            bucket,
            key,
            ExtraArgs={"Metadata": {COUNTS_METADATA: json.dumps(counts, sort_keys=True)}},
        )
    return key


def main() -> int:
    client, bucket = backup_client()
    try:
        key = run_backup(get_settings().database_url, client, bucket, datetime.now(UTC))
    except MissingToolError as error:
        print(error, file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as error:
        # Sin la dirección de la base en el mensaje: tiene la contraseña.
        print(f"pg_dump falló (código {error.returncode}): no se subió nada.", file=sys.stderr)
        return 1
    size = client.head_object(Bucket=bucket, Key=key)["ContentLength"]
    print(f"Copia OK: {key} ({size / 1024 / 1024:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
