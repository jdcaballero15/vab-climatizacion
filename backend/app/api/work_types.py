import uuid
from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep, require_role
from app.api.schemas.catalog import (
    TaskAdminOut,
    TaskCreate,
    TaskUpdate,
    WorkTypeAdminOut,
    WorkTypeCreate,
    WorkTypeUpdate,
)
from app.db.models.catalog import Task, WorkType
from app.db.models.user import User, UserRole
from app.services import catalog as catalog_service

router = APIRouter(prefix="/admin/work-types", tags=["catálogos"])

# Solo administración edita catálogos (ver roles-permisos.md). El técnico los leerá
# para cerrar órdenes por otro endpoint (E05-04).
AdminOnly = Annotated[User, Depends(require_role(UserRole.admin))]


@router.get("", response_model=list[WorkTypeAdminOut])
async def list_work_types(
    session: SessionDep, _: AdminOnly, include_inactive: bool = False
) -> Sequence[WorkType]:
    return await catalog_service.list_work_types(session, include_inactive=include_inactive)


@router.post("", response_model=WorkTypeAdminOut, status_code=status.HTTP_201_CREATED)
async def create_work_type(payload: WorkTypeCreate, session: SessionDep, _: AdminOnly) -> WorkType:
    try:
        return await catalog_service.create_work_type(session, payload)
    except catalog_service.WorkTypeNameAlreadyExistsError:
        raise _work_type_name_taken() from None


@router.get("/{work_type_id}", response_model=WorkTypeAdminOut)
async def get_work_type(work_type_id: uuid.UUID, session: SessionDep, _: AdminOnly) -> WorkType:
    try:
        return await catalog_service.get_work_type(session, work_type_id)
    except catalog_service.WorkTypeNotFoundError:
        raise _work_type_not_found() from None


@router.patch("/{work_type_id}", response_model=WorkTypeAdminOut)
async def update_work_type(
    work_type_id: uuid.UUID, payload: WorkTypeUpdate, session: SessionDep, _: AdminOnly
) -> WorkType:
    try:
        return await catalog_service.update_work_type(session, work_type_id, payload)
    except catalog_service.WorkTypeNotFoundError:
        raise _work_type_not_found() from None
    except catalog_service.WorkTypeNameAlreadyExistsError:
        raise _work_type_name_taken() from None


@router.get("/{work_type_id}/tasks", response_model=list[TaskAdminOut])
async def list_tasks(
    work_type_id: uuid.UUID, session: SessionDep, _: AdminOnly, include_inactive: bool = False
) -> Sequence[Task]:
    try:
        return await catalog_service.list_tasks(
            session, work_type_id, include_inactive=include_inactive
        )
    except catalog_service.WorkTypeNotFoundError:
        raise _work_type_not_found() from None


@router.post(
    "/{work_type_id}/tasks", response_model=TaskAdminOut, status_code=status.HTTP_201_CREATED
)
async def create_task(
    work_type_id: uuid.UUID, payload: TaskCreate, session: SessionDep, _: AdminOnly
) -> Task:
    try:
        return await catalog_service.create_task(session, work_type_id, payload)
    except catalog_service.WorkTypeNotFoundError:
        raise _work_type_not_found() from None
    except catalog_service.TaskNameAlreadyExistsError:
        raise _task_name_taken() from None


@router.patch("/{work_type_id}/tasks/{task_id}", response_model=TaskAdminOut)
async def update_task(
    work_type_id: uuid.UUID,
    task_id: uuid.UUID,
    payload: TaskUpdate,
    session: SessionDep,
    _: AdminOnly,
) -> Task:
    try:
        return await catalog_service.update_task(session, work_type_id, task_id, payload)
    except catalog_service.TaskNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "task_not_found", "message": "No se encontró la subtarea."},
        ) from None
    except catalog_service.TaskNameAlreadyExistsError:
        raise _task_name_taken() from None


def _work_type_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "work_type_not_found", "message": "No se encontró el tipo de trabajo."},
    )


def _work_type_name_taken() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "work_type_name_already_exists",
            "message": "Ya existe un tipo de trabajo con ese nombre (puede estar desactivado).",
        },
    )


def _task_name_taken() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "task_name_already_exists",
            "message": "Ese tipo de trabajo ya tiene una subtarea con ese nombre "
            "(puede estar desactivada).",
        },
    )
