import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class CountOut(BaseModel):
    key: str
    label: str
    count: int
    # Solo en los materiales: la cantidad usada (con decimales), no la cantidad de órdenes.
    quantity: Decimal | None = None


class WeekOut(BaseModel):
    week_start: date
    created: int
    done: int


class PeriodTotalsOut(BaseModel):
    date_from: date
    date_to: date
    created: int
    done: int


class MaintenanceProgressOut(BaseModel):
    generated: int
    pending: int
    assigned: int
    closed: int
    cancelled: int


class UnbilledOrderOut(BaseModel):
    id: uuid.UUID
    number: int
    client_name: str
    closed_at: datetime | None
    days: int | None


class DashboardOut(BaseModel):
    """El tablero con los filtros aplicados (E10). Sin precios ni importes."""

    date_from: date
    date_to: date
    by_status: list[CountOut]
    weeks: list[WeekOut]
    totals: PeriodTotalsOut
    # El período para comparar (E10-08, criterio 2), si se pidió.
    compare: PeriodTotalsOut | None
    by_technician: list[CountOut]
    in_progress_by_crew: list[CountOut]
    top_failures: list[CountOut]
    top_repairs: list[CountOut]
    other_failures: list[CountOut]
    other_repairs: list[CountOut]
    maintenance: MaintenanceProgressOut
    unbilled: list[UnbilledOrderOut]
    top_parts: list[CountOut]
