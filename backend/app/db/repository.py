import uuid
from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import TimestampedBase


class BaseRepository[ModelT: TimestampedBase]:
    """Repositorio base. Filtra deleted_at IS NULL por defecto (borrado lógico).

    Es el único lugar que decide la exclusión de borrados: las subclases y los
    servicios no vuelven a escribir ese filtro.
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _select(self, *, include_deleted: bool = False) -> Select[ModelT]:
        stmt = select(self.model)
        if not include_deleted:
            stmt = stmt.where(self.model.deleted_at.is_(None))
        return stmt

    async def list(self, *, include_deleted: bool = False) -> Sequence[ModelT]:
        result = await self.session.execute(self._select(include_deleted=include_deleted))
        return result.scalars().all()

    async def get(self, entity_id: uuid.UUID, *, include_deleted: bool = False) -> ModelT | None:
        stmt = self._select(include_deleted=include_deleted).where(self.model.id == entity_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
