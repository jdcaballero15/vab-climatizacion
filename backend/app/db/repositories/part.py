import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import distinct_on

from app.db.models.part import Part, PartPrice
from app.db.repository import BaseRepository


class PartRepository(BaseRepository[Part]):
    model = Part

    async def list_by_status(self, *, include_inactive: bool) -> Sequence[Part]:
        stmt = self._select().order_by(self.model.name)
        if not include_inactive:
            stmt = stmt.where(self.model.is_active.is_(True))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_name(self, name: str) -> Part | None:
        """Busca sin distinguir mayúsculas, activos e inactivos (misma regla que el índice)."""
        stmt = self._select().where(func.lower(self.model.name) == func.lower(name))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def current_prices(self, part_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, PartPrice]:
        """El precio vigente de cada material: el último por fecha de vigencia."""
        if not part_ids:
            return {}
        stmt = (
            select(PartPrice)
            .where(PartPrice.part_id.in_(part_ids), PartPrice.deleted_at.is_(None))
            .order_by(PartPrice.part_id, PartPrice.valid_from.desc(), PartPrice.created_at.desc())
            .ext(distinct_on(PartPrice.part_id))
        )
        result = await self.session.execute(stmt)
        return {price.part_id: price for price in result.scalars().all()}
