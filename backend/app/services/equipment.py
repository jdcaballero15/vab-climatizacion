import re
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, select, true
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.api.schemas.equipment import (
    EquipmentAdminOut,
    EquipmentCreate,
    EquipmentFileOut,
    EquipmentHistoryOrderOut,
    EquipmentTransferCreate,
    EquipmentTransferOut,
    EquipmentUpdate,
)
from app.db.models.catalog import EquipmentType, Failure, Repair, WorkType
from app.db.models.client import Client, ClientSite
from app.db.models.equipment import Equipment, EquipmentTransfer
from app.db.models.legacy_reference import LegacyReference
from app.db.models.part import Part, PartUsage
from app.db.models.user import User
from app.db.models.work_order import WorkOrder, WorkOrderClosure, WorkOrderEvent
from app.db.repositories.catalog import EquipmentTypeRepository
from app.db.repositories.equipment import EquipmentRepository
from app.domain.work_order import OPEN_STATUSES, WorkOrderEventType
from app.services import audit
from app.services import clients as clients_service

# Prefijo de los tipos sin prefijo propio, como un tipo recién creado (D-002).
DEFAULT_CODE_PREFIX = "EO"
# Veces que se reintenta el alta si dos altas simultáneas toman el mismo código.
_CODE_ATTEMPTS = 3


class EquipmentNotFoundError(Exception):
    """No existe un equipo activo con ese id."""


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
    await clients_service.check_active_site_of_client(session, client_id, data.client_site_id)
    equipment_type = await _check_type(session, data.equipment_type_id)

    for _ in range(_CODE_ATTEMPTS):
        code = await next_code(session, client, equipment_type)
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
        await clients_service.check_active_site_of_client(session, current_site.client_id, new_site)
    new_type = changes.get("equipment_type_id")
    if new_type is not None and new_type != equipment.equipment_type_id:
        await _check_type(session, new_type)
    for field, value in changes.items():
        setattr(equipment, field, value)
    await session.commit()
    await session.refresh(equipment)
    return equipment


async def _check_type(session: AsyncSession, type_id: uuid.UUID) -> EquipmentType:
    equipment_type = await EquipmentTypeRepository(session).get(type_id)
    if equipment_type is None:
        raise EquipmentTypeNotFoundError
    if not equipment_type.is_active:
        raise EquipmentTypeInactiveError
    return equipment_type


async def next_code(session: AsyncSession, client: Client, equipment_type: EquipmentType) -> str:
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


class EquipmentHasOpenOrdersError(Exception):
    """El equipo está en órdenes sin cerrar: no se da de baja (E03-07)."""

    def __init__(self, numbers: Sequence[int]) -> None:
        listed = ", ".join(f"N° {n}" for n in numbers)
        self.message = f"El equipo está en órdenes abiertas: {listed}. Cerralas o cancelalas antes."
        super().__init__(self.message)


class EquipmentNotDeletedError(Exception):
    """El equipo no está dado de baja."""


class TransferSameClientError(Exception):
    """El domicilio elegido es del mismo cliente: eso es mudarlo, no trasladarlo."""


async def list_deleted_equipment(
    session: AsyncSession, client_id: uuid.UUID
) -> Sequence[Equipment]:
    await clients_service.get_client(session, client_id, include_deleted=True)
    return await EquipmentRepository(session).list_for_client(client_id, site_id=None, deleted=True)


async def deactivate_equipment(
    session: AsyncSession, equipment_id: uuid.UUID, actor: User
) -> Equipment:
    """Baja lógica: deja de ofrecerse para órdenes nuevas y conserva su historial."""
    equipment = await get_equipment(session, equipment_id)
    open_numbers = (
        await session.scalars(
            select(WorkOrder.number)
            .where(
                WorkOrder.equipment_id == equipment.id,
                WorkOrder.status.in_(OPEN_STATUSES),
                WorkOrder.deleted_at.is_(None),
            )
            .order_by(WorkOrder.number)
        )
    ).all()
    if open_numbers:
        raise EquipmentHasOpenOrdersError(open_numbers)
    equipment.deleted_at = datetime.now(UTC)
    audit.record(session, "equipment", equipment.id, "deactivated", actor)
    await session.commit()
    await session.refresh(equipment)
    return equipment


async def restore_equipment(
    session: AsyncSession, equipment_id: uuid.UUID, actor: User
) -> Equipment:
    equipment = await EquipmentRepository(session).get(equipment_id, include_deleted=True)
    if equipment is None:
        raise EquipmentNotFoundError
    if equipment.deleted_at is None:
        raise EquipmentNotDeletedError
    equipment.deleted_at = None
    audit.record(session, "equipment", equipment.id, "restored", actor)
    await session.commit()
    await session.refresh(equipment)
    return equipment


async def transfer_equipment(
    session: AsyncSession, equipment_id: uuid.UUID, data: EquipmentTransferCreate, actor: User
) -> Equipment:
    """Pasa el equipo a un domicilio de otro cliente con código nuevo (E03-09). Queda el
    traslado con el código anterior; las órdenes anteriores siguen en el cliente de origen."""
    equipment = await get_equipment(session, equipment_id)
    from_site = await clients_service.get_site(session, equipment.client_site_id)
    to_site = await clients_service.get_site(session, data.client_site_id)
    if not to_site.is_active:
        raise clients_service.SiteInactiveError
    if to_site.client_id == from_site.client_id:
        raise TransferSameClientError
    to_client = await clients_service.get_client(session, to_site.client_id)
    equipment_type = await EquipmentTypeRepository(session).get(equipment.equipment_type_id)
    if equipment_type is None:
        raise EquipmentTypeNotFoundError
    from_code = equipment.internal_code
    for _ in range(_CODE_ATTEMPTS):
        code = await next_code(session, to_client, equipment_type)
        equipment.internal_code = code
        equipment.client_site_id = to_site.id
        session.add(
            EquipmentTransfer(
                equipment_id=equipment.id,
                from_client_id=from_site.client_id,
                from_site_id=from_site.id,
                from_code=from_code,
                to_client_id=to_client.id,
                to_site_id=to_site.id,
                to_code=code,
                transferred_by=actor.id,
            )
        )
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            equipment = await get_equipment(session, equipment_id)
            continue
        await session.refresh(equipment)
        return equipment
    raise EquipmentCodeUnavailableError


async def equipment_file(session: AsyncSession, equipment_id: uuid.UUID) -> EquipmentFileOut:
    """Ficha con traslados y trabajos (E03-05). También de un equipo dado de baja."""
    equipment = await EquipmentRepository(session).get(equipment_id, include_deleted=True)
    if equipment is None:
        raise EquipmentNotFoundError
    site = await session.get(ClientSite, equipment.client_site_id)
    if site is None:
        raise EquipmentNotFoundError
    client = await clients_service.get_client(session, site.client_id, include_deleted=True)
    equipment_type = await session.get(EquipmentType, equipment.equipment_type_id)
    return EquipmentFileOut(
        equipment=EquipmentAdminOut.model_validate(equipment),
        client_id=client.id,
        client_name=client.name,
        client_number=client.number,
        site_label=site.label,
        site_address=site.address,
        equipment_type_name=equipment_type.name if equipment_type else "",
        transfers=await _transfers(session, equipment.id),
        orders=await _history(session, equipment.id, client.id),
    )


async def _transfers(session: AsyncSession, equipment_id: uuid.UUID) -> list[EquipmentTransferOut]:
    from_client = aliased(Client)
    to_client = aliased(Client)
    rows = await session.execute(
        select(EquipmentTransfer, from_client.name, to_client.name, User.full_name)
        .join(from_client, from_client.id == EquipmentTransfer.from_client_id)
        .join(to_client, to_client.id == EquipmentTransfer.to_client_id)
        .join(User, User.id == EquipmentTransfer.transferred_by)
        .where(EquipmentTransfer.equipment_id == equipment_id)
        .order_by(EquipmentTransfer.transferred_at)
    )
    return [
        EquipmentTransferOut(
            from_client_name=from_name,
            from_code=transfer.from_code,
            to_client_name=to_name,
            to_code=transfer.to_code,
            transferred_by_name=by_name,
            transferred_at=transfer.transferred_at,
        )
        for transfer, from_name, to_name, by_name in rows.all()
    ]


async def _history(
    session: AsyncSession, equipment_id: uuid.UUID, current_client_id: uuid.UUID
) -> list[EquipmentHistoryOrderOut]:
    created = (
        select(WorkOrderEvent.occurred_at)
        .where(
            WorkOrderEvent.work_order_id == WorkOrder.id,
            WorkOrderEvent.event_type == WorkOrderEventType.created,
        )
        .limit(1)
        .scalar_subquery()
    )
    last_closure = (
        select(WorkOrderClosure)
        .where(
            WorkOrderClosure.work_order_id == WorkOrder.id,
            WorkOrderClosure.deleted_at.is_(None),
        )
        .order_by(WorkOrderClosure.closed_at.desc())
        .limit(1)
        .lateral()
    )
    closure = aliased(WorkOrderClosure, last_closure)
    imported = (
        select(LegacyReference.id)
        .where(LegacyReference.entity == "work_order", LegacyReference.entity_id == WorkOrder.id)
        .exists()
    )
    rows = await session.execute(
        select(
            WorkOrder,
            func.coalesce(created, WorkOrder.created_at),
            WorkType.name,
            Client.name,
            closure,
            Failure.name,
            Repair.name,
            imported,
        )
        .join(WorkType, WorkType.id == WorkOrder.work_type_id)
        .join(Client, Client.id == WorkOrder.client_id)
        .outerjoin(closure, true())
        .outerjoin(Failure, Failure.id == closure.failure_id)
        .outerjoin(Repair, Repair.id == closure.repair_id)
        .where(WorkOrder.equipment_id == equipment_id, WorkOrder.deleted_at.is_(None))
        .order_by(func.coalesce(created, WorkOrder.created_at).desc(), WorkOrder.number.desc())
    )
    items = rows.all()
    materials = await _materials(session, [row[0].id for row in items])
    return [
        EquipmentHistoryOrderOut(
            id=order.id,
            number=order.number,
            status=order.status,
            work_type_name=work_type_name,
            client_name=client_name,
            created_at=created_at,
            closed_at=last.closed_at if last is not None else None,
            failure=(failure or (last.failure_other_text if last is not None else None)),
            repair=(repair or (last.repair_other_text if last is not None else None)),
            observation=last.observation if last is not None else None,
            materials=materials.get(order.id, []),
            before_transfer=order.client_id != current_client_id,
            imported=bool(was_imported),
        )
        for (
            order,
            created_at,
            work_type_name,
            client_name,
            last,
            failure,
            repair,
            was_imported,
        ) in items
    ]


async def _materials(
    session: AsyncSession, order_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, list[str]]:
    """Los materiales de cada orden como "Nombre x cantidad", sin precios."""
    if not order_ids:
        return {}
    rows = await session.execute(
        select(
            PartUsage.work_order_id, Part.name, PartUsage.other_text, PartUsage.quantity, Part.unit
        )
        .outerjoin(Part, Part.id == PartUsage.part_id)
        .where(PartUsage.work_order_id.in_(order_ids), PartUsage.deleted_at.is_(None))
        .order_by(PartUsage.created_at)
    )
    out: dict[uuid.UUID, list[str]] = {}
    for order_id, name, other, quantity, unit in rows.all():
        amount = f"{quantity.normalize():f}"
        label = f"{name or other} x {amount}" + (f" {unit}" if unit else "")
        out.setdefault(order_id, []).append(label)
    return out
