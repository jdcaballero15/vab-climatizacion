"""Comprobantes de retiro y devolución (E09-01, E09-02) e informe mensual (E09-04).

Los comprobantes se guardan en el bucket la primera vez y después se devuelve el mismo
archivo. El informe mensual se arma al pedirlo: el mismo período da el mismo contenido.
Sin precios en ninguno (Gonza, 2026-11-10). Retiro y devolución llevan nombre y firma, sin
DNI (decisión del 2026-11-03).
"""

import calendar
import uuid
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.dates import BUSINESS_TZ
from app.core.storage import ObjectStorage
from app.db.models.catalog import Failure, Repair, WorkType
from app.db.models.client import Client, ClientSite
from app.db.models.crew import Crew, FieldTechnician
from app.db.models.document import DocumentKind, OrderDocument
from app.db.models.equipment import Equipment
from app.db.models.part import Part, PartUsage
from app.db.models.signature import Signature
from app.db.models.stored_file import StoredFile
from app.db.models.user import User
from app.db.models.work_order import (
    WorkOrder,
    WorkOrderAssignment,
    WorkOrderClosure,
    WorkOrderClosureTechnician,
    WorkOrderEvent,
)
from app.domain.work_order import (
    ClosureOutcome,
    EquipmentCondition,
    OrderStatus,
    WorkOrderEventType,
    WorkshopStage,
)
from app.services import pdf

_STAGES = {
    DocumentKind.pickup_receipt: (WorkshopStage.pickup, "Comprobante de retiro"),
    DocumentKind.delivery_receipt: (WorkshopStage.delivery, "Comprobante de devolución"),
}
_CONDITIONS = {
    EquipmentCondition.working: "Funcionando bien",
    EquipmentCondition.working_with_notes: "Funcionando con observaciones",
    EquipmentCondition.not_working: "No funciona",
}
PDF = "application/pdf"


class OrderNotFoundError(Exception):
    pass


class StageNotDoneError(Exception):
    code = "stage_not_done"

    def __init__(self, kind: DocumentKind) -> None:
        stage = "el retiro" if kind == DocumentKind.pickup_receipt else "la devolución"
        self.message = f"El comprobante sale cuando la escuadrilla cierra {stage} con firma."
        super().__init__(self.message)


class ClientNotFoundError(Exception):
    pass


class EmptyReportError(Exception):
    """Sin trabajos en el mes no hay informe (E09-04, criterio 2)."""

    code = "empty_report"
    message = "El cliente no tiene trabajos en ese mes: no hay informe."


async def receipt_url(
    session: AsyncSession,
    storage: ObjectStorage,
    order_id: uuid.UUID,
    kind: DocumentKind,
    actor: User,
) -> str:
    """URL firmada del comprobante; lo arma y lo guarda solo la primera vez."""
    order = await session.scalar(
        select(WorkOrder).where(WorkOrder.id == order_id, WorkOrder.deleted_at.is_(None))
    )
    if order is None:
        raise OrderNotFoundError
    existing = await session.scalar(
        select(StoredFile.object_key)
        .join(OrderDocument, OrderDocument.file_id == StoredFile.id)
        .where(
            OrderDocument.work_order_id == order.id,
            OrderDocument.kind == kind,
            OrderDocument.deleted_at.is_(None),
        )
    )
    if existing is not None:
        return storage.download_url(existing)
    data = await _receipt_data(session, storage, order, kind)
    content = pdf.build_receipt(data)
    file = StoredFile(
        purpose=kind.value,
        object_key=f"documents/{order.id}/{kind.value}-{uuid.uuid4()}.pdf",
        content_type=PDF,
        size_bytes=len(content),
        uploaded_by=actor.id,
        confirmed_at=datetime.now(BUSINESS_TZ),
    )
    await storage.put_bytes(file.object_key, content, PDF)
    session.add(file)
    await session.flush()
    session.add(
        OrderDocument(work_order_id=order.id, kind=kind, file_id=file.id, created_by=actor.id)
    )
    await session.commit()
    return storage.download_url(file.object_key)


async def _receipt_data(
    session: AsyncSession, storage: ObjectStorage, order: WorkOrder, kind: DocumentKind
) -> pdf.ReceiptData:
    stage, title = _STAGES[kind]
    closure = await session.scalar(
        select(WorkOrderClosure)
        .where(
            WorkOrderClosure.work_order_id == order.id,
            WorkOrderClosure.workshop_stage == stage,
            WorkOrderClosure.outcome == ClosureOutcome.done,
            WorkOrderClosure.deleted_at.is_(None),
        )
        .order_by(WorkOrderClosure.closed_at.desc())
        .limit(1)
    )
    signature = (
        await session.scalar(
            select(Signature).where(
                Signature.closure_id == closure.id, Signature.deleted_at.is_(None)
            )
        )
        if closure is not None
        else None
    )
    if closure is None or signature is None:
        raise StageNotDoneError(kind)
    client = await session.get(Client, order.client_id)
    site = await session.get(ClientSite, order.client_site_id)
    equipment = await session.get(Equipment, order.equipment_id) if order.equipment_id else None
    image = await session.get(StoredFile, signature.image_file_id)
    crew = await session.scalar(
        select(Crew.name)
        .join(WorkOrderAssignment, WorkOrderAssignment.crew_id == Crew.id)
        .where(
            WorkOrderAssignment.work_order_id == order.id,
            WorkOrderAssignment.assigned_at <= closure.closed_at,
        )
        .order_by(WorkOrderAssignment.assigned_at.desc())
        .limit(1)
    )
    technicians = (
        await session.scalars(
            select(FieldTechnician.full_name)
            .join(
                WorkOrderClosureTechnician,
                WorkOrderClosureTechnician.field_technician_id == FieldTechnician.id,
            )
            .where(WorkOrderClosureTechnician.closure_id == closure.id)
            .order_by(FieldTechnician.full_name)
        )
    ).all()
    return pdf.ReceiptData(
        title=title,
        order_number=order.number,
        client_name=client.name if client else "",
        client_number=client.number if client else "",
        site=(site.label + " · " if site and site.label else "") + (site.address if site else ""),
        equipment=(f"{equipment.internal_code} · {equipment.location_note}" if equipment else None),
        done_at=closure.closed_at.astimezone(BUSINESS_TZ),
        crew=crew,
        technicians=list(technicians),
        condition=_CONDITIONS.get(closure.equipment_condition)
        if closure.equipment_condition
        else None,
        signer_name=signature.signer_name,
        signature_png=await storage.get_bytes(image.object_key) if image else None,
        work_lines=(
            await _work_lines(session, order) if kind == DocumentKind.delivery_receipt else []
        ),
    )


async def _work_lines(session: AsyncSession, order: WorkOrder) -> list[str]:
    """Lo hecho en el galpón y los materiales, sin precios (decisión del 2026-11-10)."""
    lines: list[str] = []
    workshop = await session.scalar(
        select(WorkOrderClosure)
        .where(
            WorkOrderClosure.work_order_id == order.id,
            WorkOrderClosure.workshop_stage == WorkshopStage.workshop,
            WorkOrderClosure.outcome == ClosureOutcome.done,
            WorkOrderClosure.deleted_at.is_(None),
        )
        .order_by(WorkOrderClosure.closed_at.desc())
        .limit(1)
    )
    if workshop is not None:
        failure = await session.get(Failure, workshop.failure_id) if workshop.failure_id else None
        repair = await session.get(Repair, workshop.repair_id) if workshop.repair_id else None
        if failure or workshop.failure_other_text:
            lines.append(f"Falla: {failure.name if failure else workshop.failure_other_text}")
        if repair or workshop.repair_other_text:
            lines.append(f"Reparación: {repair.name if repair else workshop.repair_other_text}")
        if workshop.observation:
            lines.append(f"Observación: {workshop.observation}")
    rows = await session.execute(
        select(Part.name, PartUsage.other_text, PartUsage.quantity, Part.unit)
        .outerjoin(Part, Part.id == PartUsage.part_id)
        .where(PartUsage.work_order_id == order.id, PartUsage.deleted_at.is_(None))
        .order_by(PartUsage.created_at)
    )
    for name, other, quantity, unit in rows.all():
        amount = f"{quantity.normalize():f}"
        lines.append(f"Material: {name or other} x {amount}" + (f" {unit}" if unit else ""))
    return lines


async def monthly_report(
    session: AsyncSession, client_id: uuid.UUID, year: int, month: int
) -> bytes:
    """Informe del mes del cliente: sus trabajos terminados, con fecha, equipo, tipo, falla
    y reparación (E09-04). Solo órdenes de ese cliente y del sistema nuevo."""
    client = await session.get(Client, client_id)
    if client is None:
        raise ClientNotFoundError
    start = datetime.combine(date(year, month, 1), time.min, tzinfo=BUSINESS_TZ)
    last_day = calendar.monthrange(year, month)[1]
    end = start + timedelta(days=last_day)
    closure = aliased(WorkOrderClosure)
    finished = (
        select(WorkOrderEvent.work_order_id, WorkOrderEvent.occurred_at)
        .where(
            WorkOrderEvent.event_type == WorkOrderEventType.status_change,
            WorkOrderEvent.to_status == OrderStatus.done,
            WorkOrderEvent.occurred_at >= start,
            WorkOrderEvent.occurred_at < end,
        )
        .subquery()
    )
    rows = (
        await session.execute(
            select(WorkOrder, finished.c.occurred_at, WorkType.name, Equipment, closure)
            .join(finished, finished.c.work_order_id == WorkOrder.id)
            .join(WorkType, WorkType.id == WorkOrder.work_type_id)
            .outerjoin(Equipment, Equipment.id == WorkOrder.equipment_id)
            .outerjoin(
                closure,
                (closure.work_order_id == WorkOrder.id)
                & (closure.outcome == ClosureOutcome.done)
                & closure.deleted_at.is_(None),
            )
            .where(WorkOrder.client_id == client.id, WorkOrder.deleted_at.is_(None))
            .order_by(finished.c.occurred_at, WorkOrder.number)
        )
    ).all()
    lines: list[pdf.ReportLine] = []
    seen: set[uuid.UUID] = set()
    for order, finished_at, work_type, equipment, last in rows:
        if order.id in seen:
            continue
        seen.add(order.id)
        failure = await session.get(Failure, last.failure_id) if last and last.failure_id else None
        repair = await session.get(Repair, last.repair_id) if last and last.repair_id else None
        lines.append(
            pdf.ReportLine(
                date=f"{finished_at.astimezone(BUSINESS_TZ):%d/%m/%Y}",
                number=order.number,
                equipment=(
                    f"{equipment.internal_code} {equipment.location_note}" if equipment else "-"
                ),
                work_type=work_type,
                failure=(failure.name if failure else (last.failure_other_text if last else ""))
                or "",
                repair=(repair.name if repair else (last.repair_other_text if last else "")) or "",
            )
        )
    if not lines:
        raise EmptyReportError
    return pdf.build_monthly_report(
        pdf.MonthlyReportData(
            client_name=client.name,
            client_number=client.number,
            period=f"{_MONTHS[month - 1]} de {year}",
            lines=lines,
            generated_for=end,
        )
    )


_MONTHS = (
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
)
