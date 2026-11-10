"""Lotes de importación (E11-05): listarlos y deshacer uno entero, con borrado lógico."""

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.client import Client, ClientContact, ClientSite
from app.db.models.equipment import Equipment
from app.db.models.import_batch import ImportBatch
from app.db.models.legacy_reference import LegacyReference
from app.db.models.work_order import WorkOrder
from app.domain.work_order import OrderSource


class BatchNotFoundError(Exception):
    pass


class BatchAlreadyUndoneError(Exception):
    pass


class BatchInUseError(Exception):
    """Lo importado ya tiene órdenes nuevas: deshacerlo las dejaría colgadas (criterio 3)."""

    def __init__(self, numbers: Sequence[int]) -> None:
        listed = ", ".join(f"N° {n}" for n in numbers[:10])
        more = f" y {len(numbers) - 10} más" if len(numbers) > 10 else ""
        self.message = f"Hay órdenes nuevas sobre lo importado: {listed}{more}."
        super().__init__(self.message)


async def list_batches(session: AsyncSession) -> Sequence[ImportBatch]:
    return (
        await session.scalars(select(ImportBatch).order_by(ImportBatch.started_at.desc()))
    ).all()


async def undo_batch(session: AsyncSession, batch_id: uuid.UUID) -> ImportBatch:
    """Da de baja todo lo que creó el lote y sus referencias; no toca lo demás."""
    batch = await session.get(ImportBatch, batch_id)
    if batch is None:
        raise BatchNotFoundError
    if batch.undone_at is not None:
        raise BatchAlreadyUndoneError
    refs = (
        await session.scalars(
            select(LegacyReference).where(
                LegacyReference.batch_id == batch.id, LegacyReference.deleted_at.is_(None)
            )
        )
    ).all()
    ids: dict[str, list[uuid.UUID]] = {}
    for ref in refs:
        ids.setdefault(ref.entity, []).append(ref.entity_id)
    clients = ids.get("client", [])
    equipment = ids.get("equipment", [])
    in_use = (
        await session.scalars(
            select(WorkOrder.number)
            .where(
                WorkOrder.source != OrderSource.persat,
                WorkOrder.deleted_at.is_(None),
                WorkOrder.client_id.in_(clients) | WorkOrder.equipment_id.in_(equipment),
            )
            .order_by(WorkOrder.number)
        )
    ).all()
    if in_use:
        raise BatchInUseError(in_use)

    now = datetime.now(UTC)
    alive = {"deleted_at": now}
    await session.execute(
        update(WorkOrder)
        .where(WorkOrder.id.in_(ids.get("work_order", [])), WorkOrder.deleted_at.is_(None))
        .values(alive)
    )
    await session.execute(
        update(Equipment)
        .where(Equipment.id.in_(equipment), Equipment.deleted_at.is_(None))
        .values(alive)
    )
    for model in (ClientContact, ClientSite):
        await session.execute(
            update(model)
            .where(model.client_id.in_(clients), model.deleted_at.is_(None))
            .values(alive)
        )
    await session.execute(
        update(Client).where(Client.id.in_(clients), Client.deleted_at.is_(None)).values(alive)
    )
    await session.execute(
        update(LegacyReference).where(LegacyReference.batch_id == batch.id).values(alive)
    )
    batch.undone_at = now
    await session.commit()
    return batch
