"""Materiales y su lista de precios (E02-05, E02-06)."""

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.part import (
    PartAdminOut,
    PartChoiceTechnicianOut,
    PartCreate,
    PartPriceUpdate,
    PartUpdate,
)
from app.db.models.part import Part, PartPrice
from app.db.models.user import User
from app.db.repositories.part import PartRepository


class PartNotFoundError(Exception):
    """No existe un material con ese id."""


class PartNameAlreadyExistsError(Exception):
    """Otro material, activo o inactivo, ya usa ese nombre."""


async def list_parts(session: AsyncSession, *, include_inactive: bool) -> list[PartAdminOut]:
    repo = PartRepository(session)
    parts = await repo.list_by_status(include_inactive=include_inactive)
    prices = await repo.current_prices([part.id for part in parts])
    return [_out(part, prices[part.id]) for part in parts]


async def create_part(session: AsyncSession, data: PartCreate, actor: User | None) -> PartAdminOut:
    """Da de alta el material con precio 0: administración lo completa después."""
    if await PartRepository(session).get_by_name(data.name) is not None:
        raise PartNameAlreadyExistsError
    part = Part(name=data.name, unit=data.unit, is_active=True)
    session.add(part)
    await session.flush()
    price = PartPrice(
        part_id=part.id, list_price=Decimal("0"), created_by=actor.id if actor else None
    )
    session.add(price)
    await _commit(session)
    await session.refresh(part)
    await session.refresh(price)
    return _out(part, price)


async def update_part(session: AsyncSession, part_id: uuid.UUID, data: PartUpdate) -> PartAdminOut:
    repo = PartRepository(session)
    part = await _get(session, part_id)
    if data.name is not None:
        existing = await repo.get_by_name(data.name)
        if existing is not None and existing.id != part.id:
            raise PartNameAlreadyExistsError
        part.name = data.name
    if data.unit is not None:
        part.unit = data.unit
    if data.is_active is not None:
        part.is_active = data.is_active
    await _commit(session)
    await session.refresh(part)
    prices = await repo.current_prices([part.id])
    return _out(part, prices[part.id])


async def set_price(
    session: AsyncSession, part_id: uuid.UUID, data: PartPriceUpdate, actor: User
) -> PartAdminOut:
    """Agrega un precio vigente desde ahora. Los anteriores se conservan (E02-06, criterio 1)."""
    part = await _get(session, part_id)
    price = PartPrice(part_id=part.id, list_price=data.list_price, created_by=actor.id)
    session.add(price)
    await session.commit()
    await session.refresh(part)
    await session.refresh(price)
    return _out(part, price)


async def current_price_map(
    session: AsyncSession, part_ids: Sequence[uuid.UUID]
) -> dict[uuid.UUID, Decimal]:
    prices = await PartRepository(session).current_prices(part_ids)
    return {part_id: price.list_price for part_id, price in prices.items()}


async def list_active_choices(session: AsyncSession) -> list[PartChoiceTechnicianOut]:
    parts = await PartRepository(session).list_by_status(include_inactive=False)
    return [PartChoiceTechnicianOut(id=p.id, name=p.name, unit=p.unit) for p in parts]


@dataclass(frozen=True)
class ImportResult:
    created: int
    skipped: int


async def import_parts(session: AsyncSession, rows: Iterable[tuple[str, str]]) -> ImportResult:
    """Carga inicial de la lista: crea los que faltan con precio 0 y saltea los que ya están.

    Se puede repetir sin duplicar. Sin unidad, queda "unidad".
    """
    created = skipped = 0
    for name, unit in rows:
        data = PartCreate(name=name, unit=unit.strip() or "unidad")
        try:
            await create_part(session, data, None)
        except PartNameAlreadyExistsError:
            skipped += 1
        else:
            created += 1
    return ImportResult(created=created, skipped=skipped)


async def _get(session: AsyncSession, part_id: uuid.UUID) -> Part:
    part = await PartRepository(session).get(part_id)
    if part is None:
        raise PartNotFoundError
    return part


async def _commit(session: AsyncSession) -> None:
    # Dos altas con el mismo nombre a la vez: el índice único decide.
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise PartNameAlreadyExistsError from None


def _out(part: Part, price: PartPrice) -> PartAdminOut:
    return PartAdminOut(
        id=part.id,
        name=part.name,
        unit=part.unit,
        is_active=part.is_active,
        list_price=price.list_price,
        price_updated_at=price.valid_from,
    )
