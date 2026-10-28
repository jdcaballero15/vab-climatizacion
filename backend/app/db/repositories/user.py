from collections.abc import Sequence

from sqlalchemy import func

from app.db.models.user import User
from app.db.repository import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str, *, include_deleted: bool = False) -> User | None:
        stmt = self._select(include_deleted=include_deleted).where(self.model.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_name(self) -> Sequence[User]:
        """Por nombre: sin orden, Postgres devuelve al final la fila recién modificada."""
        stmt = self._select().order_by(func.lower(self.model.full_name), self.model.id)
        result = await self.session.execute(stmt)
        return result.scalars().all()
