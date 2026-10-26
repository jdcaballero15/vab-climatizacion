import uuid
from collections.abc import Collection, Sequence

from sqlalchemy import BigInteger, cast, func, select

from app.db.models.client import Client, ClientContact, ClientSegment, ClientSite
from app.db.repository import BaseRepository


class ClientRepository(BaseRepository[Client]):
    model = Client

    async def max_numeric_number(self) -> int | None:
        """Mayor número de cliente hecho solo de dígitos, contando los dados de baja.

        Los números con letras (serie CLI- de Persat) no cuentan para la serie.
        """
        stmt = select(func.max(cast(self.model.number, BigInteger))).where(
            self.model.number.regexp_match("^[0-9]+$")
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_number(self, number: str) -> Client | None:
        stmt = self._select(include_deleted=True).where(self.model.number == number)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_page(
        self, *, segment: ClientSegment | None, limit: int, offset: int
    ) -> tuple[Sequence[Client], int]:
        stmt = self._select()
        if segment is not None:
            stmt = stmt.where(self.model.segment == segment)
        total = await self.session.scalar(select(func.count()).select_from(stmt.subquery()))
        result = await self.session.execute(
            stmt.order_by(self.model.name, self.model.number).limit(limit).offset(offset)
        )
        return result.scalars().all(), total or 0


class ClientContactRepository(BaseRepository[ClientContact]):
    model = ClientContact

    async def list_for_client(self, client_id: uuid.UUID) -> Sequence[ClientContact]:
        stmt = (
            self._select()
            .where(self.model.client_id == client_id)
            .order_by(self.model.created_at, self.model.id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_for_client(
        self, client_id: uuid.UUID, contact_id: uuid.UUID
    ) -> ClientContact | None:
        stmt = self._select().where(self.model.client_id == client_id, self.model.id == contact_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_site(self, site_id: uuid.UUID) -> Sequence[ClientContact]:
        stmt = (
            self._select()
            .where(self.model.client_site_id == site_id)
            .order_by(self.model.created_at, self.model.id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_for_sites(self, site_ids: Collection[uuid.UUID]) -> Sequence[ClientContact]:
        """Contactos de varios domicilios en una consulta (lista de órdenes del técnico)."""
        stmt = (
            self._select()
            .where(self.model.client_site_id.in_(site_ids))
            .order_by(self.model.created_at, self.model.id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()


class ClientSiteRepository(BaseRepository[ClientSite]):
    model = ClientSite

    async def list_for_client(self, client_id: uuid.UUID) -> Sequence[ClientSite]:
        """Todos los domicilios del cliente, activos e inactivos, en orden de alta."""
        stmt = (
            self._select()
            .where(self.model.client_id == client_id)
            .order_by(self.model.created_at, self.model.id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
