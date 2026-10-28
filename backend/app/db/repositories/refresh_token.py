import uuid
from datetime import datetime

from sqlalchemy import update

from app.db.models.refresh_token import RefreshToken
from app.db.repository import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = self._select().where(self.model.token_hash == token_hash)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_all_for_user(self, user_id: uuid.UUID, when: datetime) -> None:
        """Revoca todos los tokens vigentes del usuario (cierra todas sus sesiones)."""
        await self.session.execute(
            update(self.model)
            .where(self.model.user_id == user_id, self.model.revoked_at.is_(None))
            .values(revoked_at=when)
        )
