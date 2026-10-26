import uuid
from collections.abc import Sequence

from sqlalchemy import func, select

from app.db.models.client import ClientSite
from app.db.models.equipment import Equipment
from app.db.repository import BaseRepository


class EquipmentRepository(BaseRepository[Equipment]):
    model = Equipment

    async def list_for_client(
        self, client_id: uuid.UUID, *, site_id: uuid.UUID | None
    ) -> Sequence[Equipment]:
        stmt = (
            self._select()
            .join(ClientSite, ClientSite.id == self.model.client_site_id)
            .where(ClientSite.client_id == client_id)
        )
        if site_id is not None:
            stmt = stmt.where(self.model.client_site_id == site_id)
        result = await self.session.execute(
            stmt.order_by(self.model.location_note, self.model.internal_code)
        )
        return result.scalars().all()

    async def count_for_client(self, client_id: uuid.UUID) -> int:
        """Equipos que tuvo el cliente, contando los dados de baja: base del correlativo."""
        stmt = (
            select(func.count())
            .select_from(self.model)
            .join(ClientSite, ClientSite.id == self.model.client_site_id)
            .where(ClientSite.client_id == client_id)
        )
        return await self.session.scalar(stmt) or 0

    async def code_exists(self, code: str) -> bool:
        stmt = self._select(include_deleted=True).where(self.model.internal_code == code)
        return await self.session.scalar(select(stmt.exists())) or False

    async def count_by_site(self, site_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, int]:
        """Equipos activos (sin dar de baja) de cada domicilio."""
        if not site_ids:
            return {}
        stmt = (
            select(self.model.client_site_id, func.count())
            .where(self.model.client_site_id.in_(site_ids), self.model.deleted_at.is_(None))
            .group_by(self.model.client_site_id)
        )
        result = await self.session.execute(stmt)
        return {site_id: count for site_id, count in result}
