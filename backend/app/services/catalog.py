import uuid
from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.catalog import (
    EquipmentTypeCreate,
    EquipmentTypeUpdate,
    FailureCreate,
    FailureUpdate,
    TaskCreate,
    TaskUpdate,
    WorkTypeCreate,
    WorkTypeUpdate,
)
from app.db.models.catalog import EquipmentType, Failure, Task, WorkType
from app.db.repositories.catalog import (
    EquipmentTypeRepository,
    FailureRepository,
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


async def list_failures(
    session: AsyncSession, *, equipment_type_id: uuid.UUID | None, include_inactive: bool
) -> Sequence[Failure]:
    include_specific = True
    if equipment_type_id is not None:
        equipment_type = await get_equipment_type(session, equipment_type_id)
        # Criterio 5: un tipo desactivado no ofrece sus fallas propias; las genéricas siguen.
        include_specific = include_inactive or equipment_type.is_active
    return await FailureRepository(session).list_filtered(
        equipment_type_id=equipment_type_id,
        include_specific=include_specific,
        include_inactive=include_inactive,
    )


async def get_failure(session: AsyncSession, failure_id: uuid.UUID) -> Failure:
    failure = await FailureRepository(session).get(failure_id)
    if failure is None:
        raise FailureNotFoundError
    return failure


async def create_failure(session: AsyncSession, data: FailureCreate) -> Failure:
    if data.equipment_type_id is not None:
        await get_equipment_type(session, data.equipment_type_id)
    if await FailureRepository(session).find_conflicting(data.name, data.equipment_type_id):
        raise FailureNameAlreadyExistsError

    failure = Failure(name=data.name, equipment_type_id=data.equipment_type_id, is_active=True)
    session.add(failure)
    await _commit(session, FailureNameAlreadyExistsError)
    await session.refresh(failure)
    return failure


async def update_failure(
    session: AsyncSession, failure_id: uuid.UUID, data: FailureUpdate
) -> Failure:
    failure = await get_failure(session, failure_id)
    if data.name is not None:
        conflicting = await FailureRepository(session).find_conflicting(
            data.name, failure.equipment_type_id
        )
        if any(other.id != failure.id for other in conflicting):
            raise FailureNameAlreadyExistsError
        failure.name = data.name
    if data.is_active is not None:
        failure.is_active = data.is_active
    await _commit(session, FailureNameAlreadyExistsError)
    await session.refresh(failure)
    return failure


async def _commit(session: AsyncSession, duplicate_error: type[Exception]) -> None:
    """Confirma la transacción. Si dos guardados con el mismo nombre se cruzan,
    el índice único de la base rechaza el segundo y se informa como duplicado."""
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise duplicate_error from error
