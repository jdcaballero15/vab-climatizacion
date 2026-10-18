from datetime import UTC, datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TimestampedBase
from app.db.repository import BaseRepository
from app.db.session import SessionLocal, engine

# Criterio 4: el repositorio base excluye por defecto los registros con deleted_at.


class _SampleThing(TimestampedBase):
    __tablename__ = "sample_things_c4"

    name: Mapped[str] = mapped_column()


class _ThingRepository(BaseRepository[_SampleThing]):
    model = _SampleThing


async def test_repository_excludes_soft_deleted_by_default() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(_SampleThing.__table__.create)
    try:
        async with SessionLocal() as session:
            session.add_all(
                [
                    _SampleThing(name="vigente"),
                    _SampleThing(name="borrado", deleted_at=datetime.now(UTC)),
                ]
            )
            await session.commit()

            repository = _ThingRepository(session)

            visible = await repository.list()
            assert [thing.name for thing in visible] == ["vigente"]

            every = await repository.list(include_deleted=True)
            assert {thing.name for thing in every} == {"vigente", "borrado"}
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(_SampleThing.__table__.drop)
