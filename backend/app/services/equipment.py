import re
import uuid
from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.equipment import EquipmentCreate, EquipmentUpdate
from app.db.models.catalog import EquipmentType
from app.db.models.client import Client, ClientSite
from app.db.models.equipment import Equipment
from app.db.repositories.catalog import EquipmentTypeRepository
from app.db.repositories.client import ClientSiteRepository
from app.db.repositories.equipment import EquipmentRepository
from app.services import clients as clients_service

# Prefijo de los tipos sin prefijo propio, como un tipo recién creado (D-002).
DEFAULT_CODE_PREFIX = "EO"
# Veces que se reintenta el alta si dos altas simultáneas toman el mismo código.
_CODE_ATTEMPTS = 3


class EquipmentNotFoundError(Exception):
    """No existe un equipo activo con ese id."""


class SiteOfAnotherClientError(Exception):
    """El domicilio elegido es de otro cliente."""


class SiteInactiveError(Exception):
    """El domicilio elegido está desactivado."""


class EquipmentTypeNotFoundError(Exception):
    """No existe un tipo de equipo con ese id."""


class EquipmentTypeInactiveError(Exception):
    """El tipo de equipo elegido está desactivado."""


class EquipmentCodeUnavailableError(Exception):
    """No se pudo tomar un código libre por altas simultáneas."""


async def list_equipment(
    session: AsyncSession, client_id: uuid.UUID, *, site_id: uuid.UUID | None
) -> Sequence[Equipment]:
    await clients_service.get_client(session, client_id)
    return await EquipmentRepository(session).list_for_client(client_id, site_id=site_id)


async def get_equipment(session: AsyncSession, equipment_id: uuid.UUID) -> Equipment:
    equipment = await EquipmentRepository(session).get(equipment_id)
    if equipment is None:
        raise EquipmentNotFoundError
    return equipment


async def create_equipment(
    session: AsyncSession, client_id: uuid.UUID, data: EquipmentCreate
) -> Equipment:
    client = await clients_service.get_client(session, client_id)
    await _check_site(session, client_id, data.client_site_id)
    equipment_type = await _check_type(session, data.equipment_type_id)

    for _ in range(_CODE_ATTEMPTS):
        code = await _next_code(session, client, equipment_type)
        equipment = Equipment(internal_code=code, **data.model_dump())
        session.add(equipment)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            continue
        await session.refresh(equipment)
        return equipment
    raise EquipmentCodeUnavailableError


async def update_equipment(
    session: AsyncSession, equipment_id: uuid.UUID, data: EquipmentUpdate
) -> Equipment:
    equipment = await get_equipment(session, equipment_id)
    changes = data.model_dump(exclude_unset=True)
    # Solo se valida lo que cambia: un equipo que ya está en un domicilio o tipo
    # desactivado se sigue pudiendo editar.
    new_site = changes.get("client_site_id")
    if new_site is not None and new_site != equipment.client_site_id:
        current_site = await clients_service.get_site(session, equipment.client_site_id)
        await _check_site(session, current_site.client_id, new_site)
    new_type = changes.get("equipment_type_id")
    if new_type is not None and new_type != equipment.equipment_type_id:
        await _check_type(session, new_type)
    for field, value in changes.items():
        setattr(equipment, field, value)
    await session.commit()
    await session.refresh(equipment)
    return equipment


async def _check_site(session: AsyncSession, client_id: uuid.UUID, site_id: uuid.UUID) -> None:
    site: ClientSite | None = await ClientSiteRepository(session).get(site_id)
    if site is None:
        raise clients_service.SiteNotFoundError
    if site.client_id != client_id:
        raise SiteOfAnotherClientError
    if not site.is_active:
        raise SiteInactiveError


async def _check_type(session: AsyncSession, type_id: uuid.UUID) -> EquipmentType:
    equipment_type = await EquipmentTypeRepository(session).get(type_id)
    if equipment_type is None:
        raise EquipmentTypeNotFoundError
    if not equipment_type.is_active:
        raise EquipmentTypeInactiveError
    return equipment_type


async def _next_code(session: AsyncSession, client: Client, equipment_type: EquipmentType) -> str:
    """Prefijo del tipo + dígitos del número de cliente + correlativo (mínimo 2 dígitos).

    Los códigos migrados de Persat pueden ocupar el que tocaría: se saltea al siguiente.
    """
    repo = EquipmentRepository(session)
    prefix = equipment_type.code_prefix or DEFAULT_CODE_PREFIX
    sequence = await repo.count_for_client(client.id) + 1
    while True:
        code = f"{prefix}{_client_digits(client.number)}{sequence:02d}"
        if not await repo.code_exists(code):
            return code
        sequence += 1


def _client_digits(number: str) -> str:
    digits = re.sub(r"\D", "", number)
    # Un número sin dígitos (formatos sueltos de Persat) se usa sin separadores.
    return digits or re.sub(r"[^0-9A-Za-z]", "", number)
