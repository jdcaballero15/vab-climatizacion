import uuid
from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.crew import (
    CrewCreate,
    CrewUpdate,
    FieldTechnicianCreate,
    FieldTechnicianUpdate,
)
from app.db.models.crew import Crew, FieldTechnician
from app.db.models.user import UserRole
from app.db.repositories.crew import CrewRepository, FieldTechnicianRepository
from app.db.repositories.user import UserRepository


class CrewNotFoundError(Exception):
    """No existe una escuadrilla con ese id."""


class CrewNameAlreadyExistsError(Exception):
    """Ya hay una escuadrilla con ese nombre (también entre las inactivas)."""


class CrewUserNotAvailableError(Exception):
    """El usuario no existe, está inactivo, no es técnico o es de otra escuadrilla."""


class CrewHasOpenOrdersError(Exception):
    """La escuadrilla tiene órdenes Asignada o En curso: hay que reasignarlas antes."""


class FieldTechnicianNotFoundError(Exception):
    """No existe un técnico con ese id."""


class FieldTechnicianNameAlreadyExistsError(Exception):
    """Ya hay un técnico con ese nombre (también entre los inactivos)."""


async def list_crews(session: AsyncSession, *, include_inactive: bool) -> Sequence[Crew]:
    return await CrewRepository(session).list_by_status(include_inactive=include_inactive)


async def get_crew(session: AsyncSession, crew_id: uuid.UUID) -> Crew:
    crew = await CrewRepository(session).get(crew_id)
    if crew is None:
        raise CrewNotFoundError
    return crew


async def create_crew(session: AsyncSession, data: CrewCreate) -> Crew:
    if await CrewRepository(session).get_by_name(data.name) is not None:
        raise CrewNameAlreadyExistsError
    if data.app_user_id is not None:
        await _check_app_user(session, data.app_user_id, crew_id=None)

    crew = Crew(name=data.name, app_user_id=data.app_user_id, is_active=True)
    session.add(crew)
    await _commit_crew(session, crew)
    return crew


async def update_crew(session: AsyncSession, crew_id: uuid.UUID, data: CrewUpdate) -> Crew:
    crew = await get_crew(session, crew_id)
    if data.name is not None:
        existing = await CrewRepository(session).get_by_name(data.name)
        if existing is not None and existing.id != crew.id:
            raise CrewNameAlreadyExistsError
        crew.name = data.name
    deactivating = data.is_active is False and crew.is_active
    if deactivating and await CrewRepository(session).has_open_orders(crew.id):
        raise CrewHasOpenOrdersError
    if data.is_active is not None:
        crew.is_active = data.is_active
    # null desasocia; si no vino el campo, el usuario no se toca.
    if "app_user_id" in data.model_fields_set:
        if data.app_user_id is not None:
            await _check_app_user(session, data.app_user_id, crew_id=crew.id)
        crew.app_user_id = data.app_user_id
    await _commit_crew(session, crew)
    return crew


async def _check_app_user(
    session: AsyncSession, user_id: uuid.UUID, *, crew_id: uuid.UUID | None
) -> None:
    user = await UserRepository(session).get(user_id)
    if user is None or not user.is_active or user.role != UserRole.technician:
        raise CrewUserNotAvailableError
    other = await CrewRepository(session).get_by_app_user(user_id)
    if other is not None and other.id != crew_id:
        raise CrewUserNotAvailableError


async def _commit_crew(session: AsyncSession, crew: Crew) -> None:
    """Si dos guardados se cruzan, el índice único rechaza el segundo: se informa según
    lo que quedó repetido (el nombre o el usuario)."""
    name = crew.name
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        if await CrewRepository(session).get_by_name(name) is not None:
            raise CrewNameAlreadyExistsError from error
        raise CrewUserNotAvailableError from error
    await session.refresh(crew, ["app_user"])


async def list_field_technicians(
    session: AsyncSession, *, include_inactive: bool
) -> Sequence[FieldTechnician]:
    return await FieldTechnicianRepository(session).list_by_status(
        include_inactive=include_inactive
    )


async def get_field_technician(session: AsyncSession, technician_id: uuid.UUID) -> FieldTechnician:
    technician = await FieldTechnicianRepository(session).get(technician_id)
    if technician is None:
        raise FieldTechnicianNotFoundError
    return technician


async def create_field_technician(
    session: AsyncSession, data: FieldTechnicianCreate
) -> FieldTechnician:
    if await FieldTechnicianRepository(session).get_by_name(data.full_name) is not None:
        raise FieldTechnicianNameAlreadyExistsError
    technician = FieldTechnician(full_name=data.full_name, is_active=True)
    session.add(technician)
    await _commit_technician(session)
    await session.refresh(technician)
    return technician


async def update_field_technician(
    session: AsyncSession, technician_id: uuid.UUID, data: FieldTechnicianUpdate
) -> FieldTechnician:
    technician = await get_field_technician(session, technician_id)
    if data.full_name is not None:
        existing = await FieldTechnicianRepository(session).get_by_name(data.full_name)
        if existing is not None and existing.id != technician.id:
            raise FieldTechnicianNameAlreadyExistsError
        technician.full_name = data.full_name
    if data.is_active is not None:
        technician.is_active = data.is_active
    await _commit_technician(session)
    await session.refresh(technician)
    return technician


async def _commit_technician(session: AsyncSession) -> None:
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise FieldTechnicianNameAlreadyExistsError from error
