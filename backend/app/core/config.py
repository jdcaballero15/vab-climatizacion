from functools import lru_cache
from typing import Self

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET_KEY = "cambiar-en-cada-entorno"  # noqa: S105 (valor de desarrollo, se pisa por entorno)
MIN_SECRET_KEY_LENGTH = 32
_ASYNC_SCHEME = "postgresql+asyncpg://"


class Settings(BaseSettings):
    """Configuración leída del entorno. Nunca poner valores reales acá."""

    # Los errores no muestran los valores: tienen la clave y la contraseña de la base, y
    # en el hosting quedan en los logs.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    app_env: str = "local"
    app_secret_key: str = DEV_SECRET_KEY
    database_url: str = "postgresql+asyncpg://ot:ot@localhost:5433/ot"
    cors_origins: str = "http://localhost:5173,http://localhost:5174"

    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    # Cookie del refresh token (ADR 0010). La ruta es la que ve el navegador: los sitios
    # llaman a la API por /api, que Render (o Vite en local) reenvía sin el prefijo.
    refresh_cookie_path: str = "/api/auth"
    refresh_cookie_secure: bool = True

    # Bucket S3 compatible (E00-09): MinIO en local, Cloudflare R2 en la nube.
    # Los valores por defecto son los de MinIO local; en la nube se pisan por entorno.
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minio"
    s3_secret_key: str = "minio12345"  # noqa: S105 (valor de desarrollo, se pisa por entorno)
    s3_bucket: str = "ot-files"
    s3_region: str = "us-east-1"  # R2 usa "auto"
    signed_url_ttl_seconds: int = 300
    upload_max_bytes: int = 5 * 1024 * 1024
    upload_allowed_types: str = "image/jpeg,image/png,image/webp,application/pdf"

    # Contraseña de los usuarios del generador de datos de prueba. Sin valor por defecto.
    seed_password: str | None = None

    @field_validator("database_url")
    @classmethod
    def _async_database_url(cls, value: str) -> str:
        """Acepta la dirección como la da el proveedor (`postgres://`, `sslmode=`).

        El driver asyncpg necesita su esquema y recibe el modo SSL como `ssl=`.
        """
        for scheme in ("postgres://", "postgresql://"):
            if value.startswith(scheme):
                value = _ASYNC_SCHEME + value.removeprefix(scheme)
        return value.replace("sslmode=", "ssl=")

    @model_validator(mode="after")
    def _real_secret_in_production(self) -> Self:
        if self.app_env == "production" and (
            self.app_secret_key == DEV_SECRET_KEY
            or len(self.app_secret_key) < MIN_SECRET_KEY_LENGTH
        ):
            raise ValueError(
                "APP_SECRET_KEY: en producción hace falta una clave aleatoria de "
                f"{MIN_SECRET_KEY_LENGTH} caracteres o más."
            )
        return self

    @property
    def upload_allowed_type_list(self) -> list[str]:
        return [t.strip() for t in self.upload_allowed_types.split(",") if t.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
