"""Registro de cambios sobre entidades que no son órdenes (E12-02; base de E12-01)."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit import AuditEvent
from app.db.models.user import User


def record(
    session: AsyncSession,
    entity: str,
    entity_id: uuid.UUID,
    action: str,
    actor: User | None,
    detail: str | None = None,
) -> None:
    """Suma el registro a la transacción en curso: se confirma con el cambio."""
    session.add(
        AuditEvent(
            entity=entity,
            entity_id=entity_id,
            action=action,
            actor_id=actor.id if actor is not None else None,
            detail=detail,
        )
    )


async def events_for(
    session: AsyncSession, entity: str, entity_id: uuid.UUID
) -> Sequence[tuple[AuditEvent, str | None]]:
    result = await session.execute(
        select(AuditEvent, User.full_name)
        .outerjoin(User, User.id == AuditEvent.actor_id)
        .where(AuditEvent.entity == entity, AuditEvent.entity_id == entity_id)
        .order_by(AuditEvent.occurred_at, AuditEvent.created_at)
    )
    return [(event, name) for event, name in result.all()]
