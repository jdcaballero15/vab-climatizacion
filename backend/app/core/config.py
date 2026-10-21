from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración leída del entorno. Nunca poner valores reales acá."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    app_secret_key: str = "cambiar-en-cada-entorno"  # noqa: S105 (valor de desarrollo, se pisa por entorno)
    database_url: str = "postgresql+asyncpg://ot:ot@localhost:5433/ot"
    cors_origins: str = "http://localhost:5173,http://localhost:5174"

    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
