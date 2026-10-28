import os
from collections.abc import AsyncGenerator

import pytest

# Los tests usan una base Postgres real y ficticia (regla del repo: nada de mocks
# de la base). Se apunta a una base de test aparte para no pisar datos locales.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://ot:ot@localhost:5433/ot_test")

TEST_DATABASE_URL = os.environ["DATABASE_URL"]


@pytest.fixture(autouse=True)
async def _dispose_engine() -> AsyncGenerator[None, None]:
    """Cierra las conexiones del pool al terminar cada test.

    pytest-asyncio crea un event loop por test; sin esto, una conexión del pool
    creada en un loop se reusaría en otro y falla. Disponer el engine evita eso.
    """
    yield
    from app.db.session import engine

    await engine.dispose()


@pytest.fixture(scope="session")
def bucket() -> None:
    """El bucket S3 compatible real (MinIO en local y en el CI), como la base: sin mocks."""
    from app.core.storage import get_storage

    get_storage().ensure_bucket()
