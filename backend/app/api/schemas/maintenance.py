import uuid
from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.api.schemas.catalog import CatalogName
from app.domain.work_order import OrderStatus

# Cada cuántos meses: el prototipo del cliente usa 2, 3, 4 y 6; se deja margen.
EveryMonths = Annotated[int, Field(ge=1, le=24)]
PlanNotes = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)]


class MaintenancePlanCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    equipment_id: uuid.UUID
    work_type_id: uuid.UUID
    crew_id: uuid.UUID | None = None
    every_months: EveryMonths
    next_due_on: date
    ends_on: date | None = None
    notes: PlanNotes | None = None


class MaintenancePlanUpdate(BaseModel):
    """Solo se cambian los campos enviados; crew_id, ends_on y notes en null los borran.

    El equipo no se cambia: para otro equipo se termina el plan y se crea uno nuevo.
    """

    model_config = ConfigDict(extra="forbid")

    work_type_id: uuid.UUID | None = None
    crew_id: uuid.UUID | None = None
    every_months: EveryMonths | None = None
    next_due_on: date | None = None
    ends_on: date | None = None
    notes: PlanNotes | None = None


class PlanEquipmentOut(BaseModel):
    id: uuid.UUID
    internal_code: str
    location_note: str
    equipment_type_name: str


class PlanClientOut(BaseModel):
    id: uuid.UUID
    number: str
    name: str
    site_label: str | None
    site_address: str


class PlanNamedOut(BaseModel):
    id: uuid.UUID
    name: str


class PlanOpenOrderOut(BaseModel):
    """La última orden generada que todavía no se cerró ni se canceló."""

    id: uuid.UUID
    number: int
    status: OrderStatus
    due_on: date


class MaintenancePlanAdminOut(BaseModel):
    id: uuid.UUID
    equipment: PlanEquipmentOut
    client: PlanClientOut
    work_type: PlanNamedOut
    crew: PlanNamedOut | None
    every_months: int
    next_due_on: date
    ends_on: date | None
    notes: str | None
    # Sin fin, o con fin después de hoy (criterio 3 de E07-03).
    active: bool
    open_order: PlanOpenOrderOut | None


class GeneratedOrderOut(BaseModel):
    order_id: uuid.UUID
    number: int
    client_name: str
    equipment_code: str
    due_on: date


class SkippedPlanOut(BaseModel):
    plan_id: uuid.UUID
    equipment_code: str
    # equipment_deleted o work_type_inactive.
    reason: str


class MaintenanceRunOut(BaseModel):
    """Resumen de una corrida (E07-04, criterio 5): qué se generó y qué se omitió."""

    generated: list[GeneratedOrderOut]
    skipped: list[SkippedPlanOut]


# ---- E07-01: checklist único de mantenimiento ----


class CheckStepCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: CatalogName


class CheckStepUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: CatalogName | None = None
    is_active: bool | None = None


class CheckStepOrder(BaseModel):
    """Los pasos activos en el orden nuevo: todos, sin repetir."""

    model_config = ConfigDict(extra="forbid")

    step_ids: list[uuid.UUID]


class CheckStepAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    position: int
    is_active: bool
