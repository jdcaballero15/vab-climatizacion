from sqlalchemy import inspect
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TimestampedBase
from app.db.session import engine

# Criterio 3: cualquier tabla incluye id (uuid), created_at, updated_at y deleted_at.


class _SampleWidget(TimestampedBase):
    __tablename__ = "sample_widgets_c3"

    name: Mapped[str] = mapped_column()


def _columns(conn: Connection) -> dict[str, dict[str, object]]:
    return {col["name"]: col for col in inspect(conn).get_columns("sample_widgets_c3")}


async def test_base_model_has_standard_columns() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(_SampleWidget.__table__.create)
    try:
        async with engine.connect() as conn:
            columns = await conn.run_sync(_columns)

        assert {"id", "created_at", "updated_at", "deleted_at"} <= set(columns)
        assert "UUID" in str(columns["id"]["type"]).upper()
        assert columns["created_at"]["nullable"] is False
        assert columns["updated_at"]["nullable"] is False
        assert columns["deleted_at"]["nullable"] is True
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(_SampleWidget.__table__.drop)
