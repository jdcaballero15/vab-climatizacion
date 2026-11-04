"""Checklist único de mantenimiento (E07-01) y su copia en cada orden generada.

Decisión de Gonza (2026-11-03): una sola lista de pasos para todo mantenimiento, editable
por la oficina; la escuadrilla marca cada paso OK o No OK (E07-06).
"""

import uuid
from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.maintenance import CheckStepCreate, CheckStepOrder, CheckStepUpdate
from app.db.models.maintenance import MaintenanceCheckStep
from app.db.models.work_order import WorkOrder, WorkOrderCheckItem
from app.db.repositories.maintenance import CheckStepRepository


class CheckStepNotFoundError(Exception):
    """No existe un paso con ese id."""


class CheckStepNameTakenError(Exception):
    """Ya hay un paso con ese nombre, activo o no."""


class CheckStepOrderMismatchError(Exception):
    """El orden nuevo no trae exactamente los pasos activos."""


async def list_steps(
    session: AsyncSession, *, include_inactive: bool
) -> Sequence[MaintenanceCheckStep]:
    return await CheckStepRepository(session).list_by_status(include_inactive=include_inactive)


async def create_step(session: AsyncSession, data: CheckStepCreate) -> MaintenanceCheckStep:
    repo = CheckStepRepository(session)
    if await repo.get_by_name(data.name) is not None:
        raise CheckStepNameTakenError
    step = MaintenanceCheckStep(name=data.name, position=await repo.next_position())
    session.add(step)
    await _commit(session)
    await session.refresh(step)
    return step


async def update_step(
    session: AsyncSession, step_id: uuid.UUID, data: CheckStepUpdate
) -> MaintenanceCheckStep:
    repo = CheckStepRepository(session)
    step = await repo.get(step_id)
    if step is None:
        raise CheckStepNotFoundError
    if data.name is not None:
        existing = await repo.get_by_name(data.name)
        if existing is not None and existing.id != step.id:
            raise CheckStepNameTakenError
        step.name = data.name
    if data.is_active is not None and data.is_active != step.is_active:
        step.is_active = data.is_active
        if data.is_active:
            # Reactivado vuelve al final, para no caer en medio de la lista nueva.
            step.position = await repo.next_position()
    await _commit(session)
    await session.refresh(step)
    return step


async def reorder_steps(
    session: AsyncSession, data: CheckStepOrder
) -> Sequence[MaintenanceCheckStep]:
    repo = CheckStepRepository(session)
    active = await repo.list_by_status(include_inactive=False)
    by_id = {step.id: step for step in active}
    if len(data.step_ids) != len(set(data.step_ids)) or set(data.step_ids) != set(by_id):
        raise CheckStepOrderMismatchError
    for position, step_id in enumerate(data.step_ids):
        by_id[step_id].position = position
    await session.commit()
    return await repo.list_by_status(include_inactive=False)


async def copy_to_order(session: AsyncSession, order: WorkOrder) -> None:
    """Copia los pasos activos a la orden recién generada (E07-01, criterio 3)."""
    steps = await CheckStepRepository(session).list_by_status(include_inactive=False)
    session.add_all(
        [
            WorkOrderCheckItem(
                work_order_id=order.id, step_id=step.id, position=position, name=step.name
            )
            for position, step in enumerate(steps)
        ]
    )


async def _commit(session: AsyncSession) -> None:
    try:
        await session.commit()
    except IntegrityError as error:
        # Dos guardados con el mismo nombre a la vez: el índice único rechaza el segundo.
        await session.rollback()
        raise CheckStepNameTakenError from error
