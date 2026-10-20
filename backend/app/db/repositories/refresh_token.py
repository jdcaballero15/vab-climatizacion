from app.db.models.refresh_token import RefreshToken
from app.db.repository import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = self._select().where(self.model.token_hash == token_hash)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
