"""Configuración por entorno: la base como la da el proveedor y la clave en producción."""

import pytest
from pydantic import ValidationError

from app.core.config import DEV_SECRET_KEY, Settings

REAL_KEY = "x" * 32


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("postgres://u:p@host:5432/ot", "postgresql+asyncpg://u:p@host:5432/ot"),
        ("postgresql://u:p@host/ot", "postgresql+asyncpg://u:p@host/ot"),
        ("postgresql+asyncpg://u:p@host/ot", "postgresql+asyncpg://u:p@host/ot"),
        ("postgres://u:p@host/ot?sslmode=require", "postgresql+asyncpg://u:p@host/ot?ssl=require"),
    ],
)
def test_direccion_de_la_base_del_proveedor(raw: str, expected: str) -> None:
    assert Settings(database_url=raw).database_url == expected


@pytest.mark.parametrize("key", [DEV_SECRET_KEY, "corta"])
def test_produccion_no_arranca_sin_una_clave_real(key: str) -> None:
    with pytest.raises(ValidationError, match="APP_SECRET_KEY"):
        Settings(app_env="production", app_secret_key=key)


def test_el_error_no_muestra_la_clave_ni_la_base() -> None:
    with pytest.raises(ValidationError) as error:
        Settings(
            app_env="production",
            app_secret_key="clave-filtrada",
            database_url="postgres://u:contrasena-filtrada@host/ot",
        )
    assert "filtrada" not in str(error.value)


def test_produccion_con_clave_real() -> None:
    assert Settings(app_env="production", app_secret_key=REAL_KEY).app_secret_key == REAL_KEY


def test_local_acepta_la_clave_de_desarrollo() -> None:
    assert Settings(app_env="local").app_secret_key == DEV_SECRET_KEY


STORAGE = {
    "s3_endpoint_url": "https://cuenta.r2.cloudflarestorage.com",
    "s3_access_key": "acceso-de-prueba",
    "s3_secret_key": "secreto-de-prueba",
}


@pytest.mark.parametrize("missing", list(STORAGE))
def test_la_api_en_produccion_no_arranca_sin_bucket(missing: str) -> None:
    values = {name: value for name, value in STORAGE.items() if name != missing}
    settings = Settings(app_env="production", app_secret_key=REAL_KEY, **values)
    with pytest.raises(RuntimeError, match=missing.upper()):
        settings.require_storage()


def test_la_api_en_produccion_arranca_con_bucket() -> None:
    Settings(app_env="production", app_secret_key=REAL_KEY, **STORAGE).require_storage()


def test_en_local_alcanza_minio() -> None:
    Settings(app_env="local").require_storage()
