import uuid
from collections.abc import Coroutine
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep, require_role
from app.api.schemas.stock import (
    AdjustmentCreate,
    LocationCreate,
    LocationOut,
    LocationUpdate,
    MovementOut,
    ReceiptCreate,
    StockPartOut,
    TransferCreate,
    TruckStockTechnicianOut,
)
from app.db.models.user import User, UserRole
from app.services import stock as stock_service

router = APIRouter(prefix="/admin/stock", tags=["stock"])
tech_router = APIRouter(prefix="/tech/stock", tags=["stock"])

AdminOnly = Annotated[User, Depends(require_role(UserRole.admin))]
# Dirección ve el stock (roles-permisos.md); no lo mueve.
AdminOrOwner = Annotated[User, Depends(require_role(UserRole.admin, UserRole.owner))]
Technician = Annotated[User, Depends(require_role(UserRole.technician))]

_RULE_ERRORS = (
    stock_service.LocationInactiveError,
    stock_service.CrewOnlyForTrucksError,
    stock_service.SameLocationError,
    stock_service.NotEnoughStockError,
    stock_service.ZeroAdjustmentError,
)


@router.get("/locations", response_model=list[LocationOut])
async def list_locations(
    session: SessionDep, _: AdminOrOwner, include_inactive: bool = False
) -> list[LocationOut]:
    return await stock_service.list_locations(session, include_inactive=include_inactive)


@router.post("/locations", response_model=LocationOut, status_code=status.HTTP_201_CREATED)
async def create_location(
    payload: LocationCreate, session: SessionDep, _: AdminOnly
) -> LocationOut:
    """Depósito o camioneta; la camioneta lleva su escuadrilla (E08-01)."""
    try:
        return await stock_service.create_location(session, payload)
    except stock_service.CrewNotFoundError:
        raise _error(404, "crew_not_found", "No se encontró la escuadrilla.") from None
    except stock_service.CrewAlreadyHasTruckError as exc:
        raise _error(409, exc.code, exc.message) from None
    except _RULE_ERRORS as exc:
        raise _error(422, exc.code, exc.message) from None


@router.patch("/locations/{location_id}", response_model=LocationOut)
async def update_location(
    location_id: uuid.UUID, payload: LocationUpdate, session: SessionDep, _: AdminOnly
) -> LocationOut:
    """Renombrar, cambiar la escuadrilla o desactivar; no se borra (criterio 3)."""
    try:
        return await stock_service.update_location(session, location_id, payload)
    except stock_service.LocationNotFoundError:
        raise _location_not_found() from None
    except stock_service.CrewNotFoundError:
        raise _error(404, "crew_not_found", "No se encontró la escuadrilla.") from None
    except stock_service.CrewAlreadyHasTruckError as exc:
        raise _error(409, exc.code, exc.message) from None
    except _RULE_ERRORS as exc:
        raise _error(422, exc.code, exc.message) from None


@router.get("", response_model=list[StockPartOut])
async def get_stock(
    session: SessionDep,
    _: AdminOrOwner,
    part_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
) -> list[StockPartOut]:
    """Cada repuesto con su cantidad por ubicación y el total (E08-05)."""
    return await stock_service.stock_by_part(session, part_id=part_id, location_id=location_id)


@router.get("/parts/{part_id}/movements", response_model=list[MovementOut])
async def get_part_movements(
    part_id: uuid.UUID, session: SessionDep, _: AdminOrOwner
) -> list[MovementOut]:
    """Historial de movimientos de un repuesto, el más nuevo primero (E08-07)."""
    try:
        return await stock_service.part_history(session, part_id)
    except stock_service.PartNotFoundError:
        raise _part_not_found() from None


@router.post("/receipts", response_model=MovementOut, status_code=status.HTTP_201_CREATED)
async def receive(payload: ReceiptCreate, session: SessionDep, admin: AdminOnly) -> MovementOut:
    """Ingreso de repuestos (E08-02)."""
    return await _move(stock_service.receive(session, payload, admin))


@router.post("/transfers", response_model=MovementOut, status_code=status.HTTP_201_CREATED)
async def transfer(payload: TransferCreate, session: SessionDep, admin: AdminOnly) -> MovementOut:
    """Transferencia entre ubicaciones en una sola transacción (E08-03)."""
    return await _move(stock_service.transfer(session, payload, admin))


@router.post("/adjustments", response_model=MovementOut, status_code=status.HTTP_201_CREATED)
async def adjust(payload: AdjustmentCreate, session: SessionDep, admin: AdminOnly) -> MovementOut:
    """Ajuste con motivo, positivo o negativo (E08-06)."""
    return await _move(stock_service.adjust(session, payload, admin))


@tech_router.get("", response_model=TruckStockTechnicianOut)
async def get_truck_stock(session: SessionDep, user: Technician) -> TruckStockTechnicianOut:
    """Lo que hay en la camioneta de mi escuadrilla, sin precios (E08-04, E08-05)."""
    return await stock_service.truck_for_user(session, user)


async def _move(pending: Coroutine[Any, Any, MovementOut]) -> MovementOut:
    """Espera el movimiento y traduce sus errores, iguales para los tres tipos."""
    try:
        return await pending
    except stock_service.PartNotFoundError:
        raise _part_not_found() from None
    except stock_service.LocationNotFoundError:
        raise _location_not_found() from None
    except stock_service.NotEnoughStockError as exc:
        raise _error(409, exc.code, exc.message) from None
    except _RULE_ERRORS as exc:
        raise _error(422, exc.code, exc.message) from None


def _location_not_found() -> HTTPException:
    return _error(404, "location_not_found", "No se encontró la ubicación.")


def _part_not_found() -> HTTPException:
    return _error(404, "part_not_found", "No se encontró el repuesto.")


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})
