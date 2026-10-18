from app.db.models.user import User
from app.db.repository import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        stmt = self._select().where(self.model.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
