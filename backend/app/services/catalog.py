import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import ColumnElement
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.catalog import (
    EquipmentScopedCreate,
    EquipmentScopedUpdate,
    EquipmentTypeCreate,
    EquipmentTypeUpdate,
    FailureCreate,
    FailureUpdate,
    RepairCreate,
    RepairUpdate,
    TaskCreate,
    TaskUpdate,
    WorkTypeCreate,
    WorkTypeUpdate,
)
from app.db.models.catalog import (
    EquipmentScopedCatalog,
    EquipmentType,
    Failure,
    Repair,
    Task,
    WorkType,
)
from app.db.repositories.catalog import (
    EquipmentScopedRepository,
    EquipmentTypeRepository,
    FailureRepository,
    RepairRepository,
    TaskRepository,
    WorkTypeRepository,
)


class WorkTypeNotFoundError(Exception):
    """No existe un tipo de trabajo con ese id."""


class TaskNotFoundError(Exception):
    """No existe una subtarea con ese id dentro del tipo de trabajo."""


class WorkTypeNameAlreadyExistsError(Exception):
    """Otro tipo de trabajo, activo o inactivo, ya usa ese nombre."""


class TaskNameAlreadyExistsError(Exception):
    """Otra subtarea del mismo tipo de trabajo ya usa ese nombre."""


class EquipmentTypeNotFoundError(Exception):
    """No existe un tipo de equipo con ese id."""


class EquipmentTypeNameAlreadyExistsError(Exception):
    """Otro tipo de equipo, activo o inactivo, ya usa ese nombre."""


class FailureNotFoundError(Exception):
    """No existe una falla con ese id."""


class FailureNameAlreadyExistsError(Exception):
    """Otra falla del mismo tipo de equipo, o una genérica, ya usa ese nombre."""


class RepairNotFoundError(Exception):
    """No existe una reparación con ese id."""


class RepairNameAlreadyExistsError(Exception):
    """Otra reparación del mismo tipo de equipo, o una genérica, ya usa ese nombre."""


class RepairFailureMismatchError(Exception):
    """La falla es de un tipo de equipo y la reparación es genérica o de otro tipo."""


async def list_work_types(session: AsyncSession, *, include_inactive: bool) -> Sequence[WorkType]:
    return await WorkTypeRepository(session).list_by_status(include_inactive=include_inactive)


async def get_work_type(session: AsyncSession, work_type_id: uuid.UUID) -> WorkType:
    work_type = await WorkTypeRepository(session).get(work_type_id)
    if work_type is None:
        raise WorkTypeNotFoundError
    return work_type


async def create_work_type(session: AsyncSession, data: WorkTypeCreate) -> WorkType:
    if await WorkTypeRepository(session).get_by_name(data.name) is not None:
        raise WorkTypeNameAlreadyExistsError

    work_type = WorkType(name=data.name, is_active=True)
    session.add(work_type)
    await _commit(session, WorkTypeNameAlreadyExistsError)
    await session.refresh(work_type)
    return work_type


async def update_work_type(
    session: AsyncSession, work_type_id: uuid.UUID, data: WorkTypeUpdate
) -> WorkType:
    work_type = await get_work_type(session, work_type_id)
    if data.name is not None:
        existing = await WorkTypeRepository(session).get_by_name(data.name)
        if existing is not None and existing.id != work_type.id:
            raise WorkTypeNameAlreadyExistsError
        work_type.name = data.name
    if data.is_active is not None:
        work_type.is_active = data.is_active
    await _commit(session, WorkTypeNameAlreadyExistsError)
    await session.refresh(work_type)
    return work_type


async def list_tasks(
    session: AsyncSession, work_type_id: uuid.UUID, *, include_inactive: bool
) -> Sequence[Task]:
    work_type = await get_work_type(session, work_type_id)
    # Criterio 5: un tipo desactivado no ofrece subtareas, aunque cada una siga activa.
    if not include_inactive and not work_type.is_active:
        return []
    return await TaskRepository(session).list_for_work_type(
        work_type_id, include_inactive=include_inactive
    )


async def create_task(session: AsyncSession, work_type_id: uuid.UUID, data: TaskCreate) -> Task:
    await get_work_type(session, work_type_id)
    if await TaskRepository(session).get_by_name(work_type_id, data.name) is not None:
        raise TaskNameAlreadyExistsError

    task = Task(work_type_id=work_type_id, name=data.name, is_active=True)
    session.add(task)
    await _commit(session, TaskNameAlreadyExistsError)
    await session.refresh(task)
    return task


async def update_task(
    session: AsyncSession, work_type_id: uuid.UUID, task_id: uuid.UUID, data: TaskUpdate
) -> Task:
    repo = TaskRepository(session)
    task = await repo.get(task_id)
    if task is None or task.work_type_id != work_type_id:
        raise TaskNotFoundError
    if data.name is not None:
        existing = await repo.get_by_name(work_type_id, data.name)
        if existing is not None and existing.id != task.id:
            raise TaskNameAlreadyExistsError
        task.name = data.name
    if data.is_active is not None:
        task.is_active = data.is_active
    await _commit(session, TaskNameAlreadyExistsError)
    await session.refresh(task)
    return task


async def list_equipment_types(
    session: AsyncSession, *, include_inactive: bool
) -> Sequence[EquipmentType]:
    return await EquipmentTypeRepository(session).list_by_status(include_inactive=include_inactive)


async def get_equipment_type(session: AsyncSession, equipment_type_id: uuid.UUID) -> EquipmentType:
    equipment_type = await EquipmentTypeRepository(session).get(equipment_type_id)
    if equipment_type is None:
        raise EquipmentTypeNotFoundError
    return equipment_type


async def create_equipment_type(session: AsyncSession, data: EquipmentTypeCreate) -> EquipmentType:
    if await EquipmentTypeRepository(session).get_by_name(data.name) is not None:
        raise EquipmentTypeNameAlreadyExistsError

    equipment_type = EquipmentType(name=data.name, is_active=True)
    session.add(equipment_type)
    await _commit(session, EquipmentTypeNameAlreadyExistsError)
    await session.refresh(equipment_type)
    return equipment_type


async def update_equipment_type(
    session: AsyncSession, equipment_type_id: uuid.UUID, data: EquipmentTypeUpdate
) -> EquipmentType:
    equipment_type = await get_equipment_type(session, equipment_type_id)
    if data.name is not None:
        existing = await EquipmentTypeRepository(session).get_by_name(data.name)
        if existing is not None and existing.id != equipment_type.id:
            raise EquipmentTypeNameAlreadyExistsError
        equipment_type.name = data.name
    if data.is_active is not None:
        equipment_type.is_active = data.is_active
    await _commit(session, EquipmentTypeNameAlreadyExistsError)
    await session.refresh(equipment_type)
    return equipment_type


@dataclass(frozen=True)
class _ScopedCatalog[ModelT: EquipmentScopedCatalog]:
    """Lo que cambia entre fallas y reparaciones: el modelo, su repositorio y sus errores."""

    model: type[ModelT]
    repository: type[EquipmentScopedRepository[ModelT]]
    not_found: type[Exception]
    name_taken: type[Exception]


_FAILURES = _ScopedCatalog(
    Failure, FailureRepository, FailureNotFoundError, FailureNameAlreadyExistsError
)
_REPAIRS = _ScopedCatalog(
    Repair, RepairRepository, RepairNotFoundError, RepairNameAlreadyExistsError
)


async def list_failures(
    session: AsyncSession, *, equipment_type_id: uuid.UUID | None, include_inactive: bool
) -> Sequence[Failure]:
    return await _list_scoped(session, _FAILURES, equipment_type_id, include_inactive)


async def get_failure(session: AsyncSession, failure_id: uuid.UUID) -> Failure:
    return await _get_scoped(session, _FAILURES, failure_id)


async def create_failure(session: AsyncSession, data: FailureCreate) -> Failure:
    return await _create_scoped(session, _FAILURES, data)


async def update_failure(
    session: AsyncSession, failure_id: uuid.UUID, data: FailureUpdate
) -> Failure:
    return await _update_scoped(session, _FAILURES, failure_id, data)


async def list_repairs(
    session: AsyncSession,
    *,
    equipment_type_id: uuid.UUID | None,
    failure_id: uuid.UUID | None,
    include_inactive: bool,
) -> Sequence[Repair]:
    extra_filters: list[ColumnElement[bool]] = []
    if failure_id is not None:
        failure = await get_failure(session, failure_id)
        # Una falla desactivada no ofrece sus reparaciones, como un tipo desactivado.
        if not include_inactive and not failure.is_active:
            return []
        extra_filters.append(Repair.failure_id == failure_id)
    return await _list_scoped(session, _REPAIRS, equipment_type_id, include_inactive, extra_filters)


async def get_repair(session: AsyncSession, repair_id: uuid.UUID) -> Repair:
    return await _get_scoped(session, _REPAIRS, repair_id)


async def create_repair(session: AsyncSession, data: RepairCreate) -> Repair:
    failure = await get_failure(session, data.failure_id)
    # Una falla genérica sirve para cualquier reparación; una de un tipo, solo para ese tipo.
    if (
        failure.equipment_type_id is not None
        and failure.equipment_type_id != data.equipment_type_id
    ):
        raise RepairFailureMismatchError
    return await _create_scoped(session, _REPAIRS, data, failure_id=data.failure_id)


async def update_repair(session: AsyncSession, repair_id: uuid.UUID, data: RepairUpdate) -> Repair:
    return await _update_scoped(session, _REPAIRS, repair_id, data)


async def _list_scoped[ModelT: EquipmentScopedCatalog](
    session: AsyncSession,
    catalog: _ScopedCatalog[ModelT],
    equipment_type_id: uuid.UUID | None,
    include_inactive: bool,
    extra_filters: Sequence[ColumnElement[bool]] = (),
) -> Sequence[ModelT]:
    include_specific = True
    if equipment_type_id is not None:
        equipment_type = await get_equipment_type(session, equipment_type_id)
        # Un tipo desactivado no ofrece sus valores propios; los genéricos siguen.
        include_specific = include_inactive or equipment_type.is_active
    return await catalog.repository(session).list_filtered(
        equipment_type_id=equipment_type_id,
        include_specific=include_specific,
        include_inactive=include_inactive,
        extra_filters=extra_filters,
    )


async def _get_scoped[ModelT: EquipmentScopedCatalog](
    session: AsyncSession, catalog: _ScopedCatalog[ModelT], item_id: uuid.UUID
) -> ModelT:
    item = await catalog.repository(session).get(item_id)
    if item is None:
        raise catalog.not_found
    return item


async def _create_scoped[ModelT: EquipmentScopedCatalog](
    session: AsyncSession,
    catalog: _ScopedCatalog[ModelT],
    data: EquipmentScopedCreate,
    **fields: object,
) -> ModelT:
    """`fields` son las columnas propias del catálogo (por ejemplo, la falla de una reparación)."""
    if data.equipment_type_id is not None:
        await get_equipment_type(session, data.equipment_type_id)
    if await catalog.repository(session).find_conflicting(data.name, data.equipment_type_id):
        raise catalog.name_taken

    item = catalog.model(
        name=data.name, equipment_type_id=data.equipment_type_id, is_active=True, **fields
    )
    session.add(item)
    await _commit(session, catalog.name_taken)
    await session.refresh(item)
    return item


async def _update_scoped[ModelT: EquipmentScopedCatalog](
    session: AsyncSession,
    catalog: _ScopedCatalog[ModelT],
    item_id: uuid.UUID,
    data: EquipmentScopedUpdate,
) -> ModelT:
    item = await _get_scoped(session, catalog, item_id)
    if data.name is not None:
        conflicting = await catalog.repository(session).find_conflicting(
            data.name, item.equipment_type_id
        )
        if any(other.id != item.id for other in conflicting):
            raise catalog.name_taken
        item.name = data.name
    if data.is_active is not None:
        item.is_active = data.is_active
    await _commit(session, catalog.name_taken)
    await session.refresh(item)
    return item


async def _commit(session: AsyncSession, duplicate_error: type[Exception]) -> None:
    """Confirma la transacción. Si dos guardados con el mismo nombre se cruzan,
    el índice único de la base rechaza el segundo y se informa como duplicado."""
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise duplicate_error from error
