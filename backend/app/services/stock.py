"""Stock por movimientos (E08, regla 6): el saldo de cada ubicación es la suma de lo que
entra menos lo que sale; nunca se guarda ni se edita un saldo.

Decisiones de Gonza (2026-11-10): los depósitos los carga la oficina; cada escuadrilla
tiene su camioneta; al cerrar, los materiales se descuentan de la camioneta de la
escuadrilla; sin stock suficiente se deja cerrar igual y la camioneta queda en negativo,
destacada para ajustarla.
"""

import uuid
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import ColumnElement, Subquery, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.api.schemas.stock import (
    AdjustmentCreate,
    LocationCreate,
    LocationOut,
    LocationUpdate,
    MovementOut,
    ReceiptCreate,
    StockBalanceOut,
    StockPartOut,
    TransferCreate,
    TruckItemTechnicianOut,
    TruckStockTechnicianOut,
)
from app.db.models.crew import Crew
from app.db.models.part import Part, PartUsage
from app.db.models.stock import (
    StockLocation,
    StockLocationKind,
    StockMovement,
    StockMovementKind,
)
from app.db.models.user import User
from app.db.models.work_order import WorkOrder


class LocationNotFoundError(Exception):
    pass


class LocationInactiveError(Exception):
    code = "location_inactive"
    message = "La ubicación está desactivada."


class CrewOnlyForTrucksError(Exception):
    code = "crew_only_for_trucks"
    message = "Solo una camioneta lleva escuadrilla."


class CrewAlreadyHasTruckError(Exception):
    code = "crew_already_has_truck"
    message = "Esa escuadrilla ya tiene una camioneta activa."


class CrewNotFoundError(Exception):
    pass


class PartNotFoundError(Exception):
    pass


class SameLocationError(Exception):
    code = "same_location"
    message = "El origen y el destino tienen que ser distintos."


class NotEnoughStockError(Exception):
    code = "not_enough_stock"

    def __init__(self, available: Decimal) -> None:
        self.message = f"No alcanza el stock del origen: hay {available.normalize():f}."
        super().__init__(self.message)


class ZeroAdjustmentError(Exception):
    code = "zero_adjustment"
    message = "El ajuste no puede ser cero."


# --- Ubicaciones (E08-01) ---


async def list_locations(session: AsyncSession, *, include_inactive: bool) -> list[LocationOut]:
    stmt = (
        select(StockLocation, Crew.name)
        .outerjoin(Crew, Crew.id == StockLocation.crew_id)
        .where(StockLocation.deleted_at.is_(None))
        .order_by(StockLocation.kind, StockLocation.name)
    )
    if not include_inactive:
        stmt = stmt.where(StockLocation.is_active.is_(True))
    return [_location_out(loc, crew) for loc, crew in (await session.execute(stmt)).all()]


async def create_location(session: AsyncSession, data: LocationCreate) -> LocationOut:
    if data.crew_id is not None and data.kind != StockLocationKind.truck:
        raise CrewOnlyForTrucksError
    location = StockLocation(kind=data.kind, name=data.name, crew_id=data.crew_id)
    await _check_crew(session, data.crew_id)
    session.add(location)
    return await _save(session, location)


async def update_location(
    session: AsyncSession, location_id: uuid.UUID, data: LocationUpdate
) -> LocationOut:
    location = await _location(session, location_id, active=False)
    changes = data.model_dump(exclude_unset=True)
    if "crew_id" in changes:
        if changes["crew_id"] is not None and location.kind != StockLocationKind.truck:
            raise CrewOnlyForTrucksError
        await _check_crew(session, changes["crew_id"])
    for field, value in changes.items():
        if field == "name" and value is None:
            continue
        setattr(location, field, value)
    return await _save(session, location)


async def _save(session: AsyncSession, location: StockLocation) -> LocationOut:
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise CrewAlreadyHasTruckError from None
    await session.refresh(location)
    crew = await session.get(Crew, location.crew_id) if location.crew_id else None
    return _location_out(location, crew.name if crew else None)


async def _check_crew(session: AsyncSession, crew_id: uuid.UUID | None) -> None:
    if crew_id is not None and await session.get(Crew, crew_id) is None:
        raise CrewNotFoundError


def _location_out(location: StockLocation, crew_name: str | None) -> LocationOut:
    return LocationOut(
        id=location.id,
        kind=location.kind,
        name=location.name,
        crew_id=location.crew_id,
        crew_name=crew_name,
        is_active=location.is_active,
    )


# --- Movimientos (E08-02, E08-03, E08-06) ---


async def receive(session: AsyncSession, data: ReceiptCreate, actor: User) -> MovementOut:
    await _part(session, data.part_id)
    await _location(session, data.location_id)
    movement = StockMovement(
        kind=StockMovementKind.receipt,
        part_id=data.part_id,
        quantity=data.quantity,
        to_location_id=data.location_id,
        created_by=actor.id,
    )
    return await _commit_movement(session, movement)


async def transfer(session: AsyncSession, data: TransferCreate, actor: User) -> MovementOut:
    if data.from_location_id == data.to_location_id:
        raise SameLocationError
    await _part(session, data.part_id)
    origin = await _location(session, data.from_location_id, lock=True)
    await _location(session, data.to_location_id)
    available = await balance(session, data.part_id, origin.id)
    if available < data.quantity:
        raise NotEnoughStockError(available)
    movement = StockMovement(
        kind=StockMovementKind.transfer,
        part_id=data.part_id,
        quantity=data.quantity,
        from_location_id=origin.id,
        to_location_id=data.to_location_id,
        created_by=actor.id,
    )
    return await _commit_movement(session, movement)


async def adjust(session: AsyncSession, data: AdjustmentCreate, actor: User) -> MovementOut:
    if data.quantity == 0:
        raise ZeroAdjustmentError
    await _part(session, data.part_id)
    location = await _location(session, data.location_id, active=False)
    adds = data.quantity > 0
    movement = StockMovement(
        kind=StockMovementKind.adjustment,
        part_id=data.part_id,
        quantity=abs(data.quantity),
        to_location_id=location.id if adds else None,
        from_location_id=None if adds else location.id,
        reason=data.reason,
        created_by=actor.id,
    )
    # El movimiento mismo, con motivo, usuario y fecha, es el registro del ajuste.
    return await _commit_movement(session, movement)


async def record_closure_usage(
    session: AsyncSession, crew: Crew | None, usages: Sequence[PartUsage], actor: User
) -> None:
    """Descuenta de la camioneta de la escuadrilla lo usado en el cierre (E08-04), en la
    misma transacción. Sin camioneta no hay de dónde descontar; sin stock queda en negativo
    (E08-08). Los "Otro" escritos a mano no tienen repuesto y no mueven stock."""
    parts = [usage for usage in usages if usage.part_id is not None]
    if crew is None or not parts:
        return
    truck = await session.scalar(
        select(StockLocation).where(
            StockLocation.crew_id == crew.id,
            StockLocation.is_active.is_(True),
            StockLocation.deleted_at.is_(None),
        )
    )
    if truck is None:
        return
    session.add_all(
        StockMovement(
            kind=StockMovementKind.usage,
            part_id=usage.part_id,
            quantity=usage.quantity,
            from_location_id=truck.id,
            work_order_id=usage.work_order_id,
            part_usage_id=usage.id,
            created_by=actor.id,
        )
        for usage in parts
    )


async def _commit_movement(session: AsyncSession, movement: StockMovement) -> MovementOut:
    session.add(movement)
    await session.commit()
    await session.refresh(movement)
    return (await _movements(session, StockMovement.id == movement.id))[0]


# --- Consultas (E08-05, E08-07) ---


def _balance_rows() -> Subquery:
    """Entradas y salidas por repuesto y ubicación, para sumar."""
    incoming = select(
        StockMovement.part_id.label("part_id"),
        StockMovement.to_location_id.label("location_id"),
        StockMovement.quantity.label("delta"),
    ).where(StockMovement.to_location_id.is_not(None), StockMovement.deleted_at.is_(None))
    outgoing = select(
        StockMovement.part_id,
        StockMovement.from_location_id,
        -StockMovement.quantity,
    ).where(StockMovement.from_location_id.is_not(None), StockMovement.deleted_at.is_(None))
    return incoming.union_all(outgoing).subquery()


async def balance(session: AsyncSession, part_id: uuid.UUID, location_id: uuid.UUID) -> Decimal:
    rows = _balance_rows()
    total = await session.scalar(
        select(func.coalesce(func.sum(rows.c.delta), 0)).where(
            rows.c.part_id == part_id,
            rows.c.location_id == location_id,
        )
    )
    return Decimal(total or 0)


async def stock_by_part(
    session: AsyncSession,
    *,
    part_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
) -> list[StockPartOut]:
    """Cada repuesto con su cantidad por ubicación y el total (E08-05)."""
    rows = _balance_rows()
    stmt = (
        select(
            Part.id,
            Part.name,
            Part.unit,
            StockLocation.id,
            StockLocation.name,
            func.sum(rows.c.delta),
        )
        .select_from(rows)
        .join(Part, Part.id == rows.c.part_id)
        .join(StockLocation, StockLocation.id == rows.c.location_id)
        .group_by(Part.id, Part.name, Part.unit, StockLocation.id, StockLocation.name)
        .order_by(Part.name, StockLocation.name)
    )
    if part_id is not None:
        stmt = stmt.where(Part.id == part_id)
    if location_id is not None:
        stmt = stmt.where(StockLocation.id == location_id)
    parts: dict[uuid.UUID, StockPartOut] = {}
    for pid, name, unit, loc_id, loc_name, quantity in (await session.execute(stmt)).all():
        quantity = Decimal(quantity)
        if quantity == 0:
            continue
        part = parts.setdefault(
            pid,
            StockPartOut(
                part_id=pid,
                part_name=name,
                unit=unit,
                total=Decimal(0),
                by_location=[],
                has_negative=False,
            ),
        )
        part.by_location.append(
            StockBalanceOut(
                part_id=pid,
                part_name=name,
                unit=unit,
                location_id=loc_id,
                location_name=loc_name,
                quantity=quantity,
            )
        )
        part.total += quantity
        part.has_negative = part.has_negative or quantity < 0
    return list(parts.values())


async def part_history(session: AsyncSession, part_id: uuid.UUID) -> list[MovementOut]:
    await _part(session, part_id)
    return await _movements(session, StockMovement.part_id == part_id)


async def truck_for_user(session: AsyncSession, user: User) -> TruckStockTechnicianOut:
    """La camioneta de la escuadrilla del usuario y lo que tiene, sin precios."""
    truck = await session.scalar(
        select(StockLocation)
        .join(Crew, Crew.id == StockLocation.crew_id)
        .where(
            Crew.app_user_id == user.id,
            Crew.is_active.is_(True),
            StockLocation.is_active.is_(True),
            StockLocation.deleted_at.is_(None),
        )
    )
    if truck is None:
        return TruckStockTechnicianOut(location_name=None, items=[])
    stock = await stock_by_part(session, location_id=truck.id)
    return TruckStockTechnicianOut(
        location_name=truck.name,
        items=[
            TruckItemTechnicianOut(part_name=p.part_name, unit=p.unit, quantity=p.total)
            for p in stock
        ],
    )


async def _movements(session: AsyncSession, *where: ColumnElement[bool]) -> list[MovementOut]:
    origin = aliased(StockLocation)
    target = aliased(StockLocation)
    stmt = (
        select(StockMovement, origin.name, target.name, WorkOrder.number, User.full_name)
        .outerjoin(origin, origin.id == StockMovement.from_location_id)
        .outerjoin(target, target.id == StockMovement.to_location_id)
        .outerjoin(WorkOrder, WorkOrder.id == StockMovement.work_order_id)
        .join(User, User.id == StockMovement.created_by)
        .where(StockMovement.deleted_at.is_(None), *where)
        .order_by(StockMovement.occurred_at.desc(), StockMovement.created_at.desc())
    )
    return [
        MovementOut(
            id=movement.id,
            kind=movement.kind,
            quantity=movement.quantity,
            from_location_name=from_name,
            to_location_name=to_name,
            work_order_id=movement.work_order_id,
            work_order_number=number,
            reason=movement.reason,
            created_by_name=by_name,
            occurred_at=movement.occurred_at,
        )
        for movement, from_name, to_name, number, by_name in (await session.execute(stmt)).all()
    ]


async def _part(session: AsyncSession, part_id: uuid.UUID) -> Part:
    part = await session.scalar(select(Part).where(Part.id == part_id, Part.deleted_at.is_(None)))
    if part is None:
        raise PartNotFoundError
    return part


async def _location(
    session: AsyncSession, location_id: uuid.UUID, *, active: bool = True, lock: bool = False
) -> StockLocation:
    stmt = select(StockLocation).where(
        StockLocation.id == location_id, StockLocation.deleted_at.is_(None)
    )
    if lock:
        # Dos transferencias a la vez desde el mismo origen no lo dejan en negativo.
        stmt = stmt.with_for_update()
    location = await session.scalar(stmt)
    if location is None:
        raise LocationNotFoundError
    if active and not location.is_active:
        raise LocationInactiveError
    return location
