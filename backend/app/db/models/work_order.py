import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Sequence,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampedBase
from app.domain.work_order import (
    CancelReason,
    CheckResult,
    ClosureOutcome,
    EquipmentCondition,
    NoSignatureReason,
    NotDoneReason,
    OrderChannel,
    OrderKind,
    OrderSource,
    OrderStatus,
    PaymentMethod,
    WorkOrderEventType,
    WorkshopStage,
)

ORDER_STATUS = Enum(OrderStatus, name="order_status")
WORKSHOP_STAGE = Enum(WorkshopStage, name="workshop_stage")
WORK_ORDER_NUMBER_SEQ = Sequence("work_order_number_seq")

# varchar con CHECK y no un enum de Postgres: sumar un tipo de evento no obliga a migrar
# un enum, solo a reemplazar la restricción.
EVENT_TYPE_CHECK = "event_type IN ({})".format(
    ", ".join(f"'{event_type.value}'" for event_type in WorkOrderEventType)
)


class WorkOrder(TimestampedBase):
    """Orden de trabajo. Las fechas de negocio salen de sus eventos (ADR 0005)."""

    __tablename__ = "work_order"
    __table_args__ = (
        # Una de taller siempre está en una etapa; una en el lugar, en ninguna (E06).
        CheckConstraint(
            "(kind = 'workshop') = (workshop_stage IS NOT NULL)",
            name="ck_work_order_workshop_stage",
        ),
        CheckConstraint(
            "(maintenance_plan_id IS NULL) = (maintenance_due_on IS NULL)",
            name="ck_work_order_maintenance_due",
        ),
        # Una orden por visita de cada plan: generar dos veces no duplica (E07-04).
        Index(
            "uq_work_order_maintenance_visit",
            "maintenance_plan_id",
            "maintenance_due_on",
            unique=True,
        ),
    )

    number: Mapped[int] = mapped_column(
        BigInteger,
        WORK_ORDER_NUMBER_SEQ,
        server_default=WORK_ORDER_NUMBER_SEQ.next_value(),
        unique=True,
        nullable=False,
    )
    kind: Mapped[OrderKind] = mapped_column(
        Enum(OrderKind, name="order_kind"), nullable=False, default=OrderKind.on_site
    )
    # Taller (E06): la etapa que toca ahora o, si está Terminada, la última. Van en fila;
    # entre una y otra la orden vuelve a Pendiente (opción A, 2026-11-03).
    workshop_stage: Mapped[WorkshopStage | None] = mapped_column(WORKSHOP_STAGE, nullable=True)
    source: Mapped[OrderSource] = mapped_column(
        Enum(OrderSource, name="order_source"), nullable=False, default=OrderSource.manual
    )
    # Se cambia solo con work_orders.apply_transition, junto con su evento.
    status: Mapped[OrderStatus] = mapped_column(ORDER_STATUS, nullable=False, index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("client.id"), nullable=False, index=True
    )
    client_site_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("client_site.id"), nullable=False, index=True
    )
    equipment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("equipment.id"), nullable=True, index=True
    )
    work_type_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("work_type.id"), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Obligatorio en las manuales (lo exige la API); las de mantenimiento no tienen canal.
    channel: Mapped[OrderChannel | None] = mapped_column(
        Enum(OrderChannel, name="order_channel"), nullable=True
    )
    # Quién pidió (nombre y cargo): el técnico no lo ve. Dónde (sector, piso o ala): sí.
    requester_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requester_area: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Generada por un plan de mantenimiento (E07-04): el plan y el día de la visita.
    maintenance_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("maintenance_plan.id"), nullable=True
    )
    maintenance_due_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    # La orden de la que nació, si se abrió desde un cierre (E04-13).
    source_order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("work_order.id"), nullable=True, index=True
    )
    # Las generadas por mantenimiento no se asignan hasta aprobar el lote (R6, E99-10).
    requires_approval: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )


class WorkOrderEvent(TimestampedBase):
    """Línea de tiempo de la orden: cada cambio de estado y cada hecho relevante."""

    __tablename__ = "work_order_event"
    __table_args__ = (CheckConstraint(EVENT_TYPE_CHECK, name="ck_work_order_event_type"),)

    work_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_order.id"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    from_status: Mapped[OrderStatus | None] = mapped_column(ORDER_STATUS, nullable=True)
    # Nulo en los hechos que no cambian el estado.
    to_status: Mapped[OrderStatus | None] = mapped_column(ORDER_STATUS, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class WorkOrderAssignment(TimestampedBase):
    """Escuadrilla responsable de la orden y fecha prevista (solo el día, sin hora).

    La vigente es la que no tiene unassigned_at; el índice parcial garantiza una sola
    por orden (una sola escuadrilla responsable, R7, D-013).
    """

    __tablename__ = "work_order_assignment"
    __table_args__ = (
        Index(
            "uq_work_order_assignment_current",
            "work_order_id",
            unique=True,
            postgresql_where=text("unassigned_at IS NULL AND deleted_at IS NULL"),
        ),
    )

    work_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_order.id"), nullable=False, index=True
    )
    crew_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("crew.id"), nullable=False, index=True)
    scheduled_for: Mapped[date] = mapped_column(Date, nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    unassigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Por qué administración se la devolvió a la escuadrilla (E04-08, criterio 3). Lo ve
    # la escuadrilla en el celular mientras esta asignación esté vigente.
    return_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class WorkOrderClosure(TimestampedBase):
    """Cierre de la escuadrilla (E05-04, E05-08). Uno por orden en el cierre básico."""

    __tablename__ = "work_order_closure"
    __table_args__ = (
        # El texto va solo con "Otro", y con "Otro" es obligatorio (E05-07).
        CheckConstraint(
            "(no_signature_reason IS NOT DISTINCT FROM 'other') = (no_signature_text IS NOT NULL)",
            name="ck_work_order_closure_no_signature_text",
        ),
    )

    work_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_order.id"), nullable=False, index=True
    )
    # Usuario de la escuadrilla que cerró (D-013).
    closed_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    closed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    outcome: Mapped[ClosureOutcome] = mapped_column(
        Enum(ClosureOutcome, name="closure_outcome"), nullable=False
    )
    failure_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("failure.id"), nullable=True)
    # "Otro": texto en lugar de un valor del catálogo.
    failure_other_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    repair_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("repair.id"), nullable=True)
    repair_other_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Nulo si no se pudo hacer.
    equipment_condition: Mapped[EquipmentCondition | None] = mapped_column(
        Enum(EquipmentCondition, name="equipment_condition"), nullable=True
    )
    not_done_reason: Mapped[NotDoneReason | None] = mapped_column(
        Enum(NotDoneReason, name="not_done_reason"), nullable=True
    )
    observation: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Por qué no hay firma del cliente (D-011). Nulo si hay firma; los cierres anteriores a
    # E05-07 no tienen ni firma ni motivo.
    no_signature_reason: Mapped[NoSignatureReason | None] = mapped_column(
        Enum(NoSignatureReason, name="no_signature_reason"), nullable=True
    )
    no_signature_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # La etapa de taller que cerró (E06); nula en una orden en el lugar.
    workshop_stage: Mapped[WorkshopStage | None] = mapped_column(WORKSHOP_STAGE, nullable=True)
    # La genera el celular: reenviar el mismo cierre no lo duplica (E05-12).
    idempotency_key: Mapped[uuid.UUID] = mapped_column(Uuid, unique=True, nullable=False)


class WorkOrderClosureTechnician(Base):
    """Quiénes fueron (D-013). Base de los trabajos por técnico (E10-02)."""

    __tablename__ = "work_order_closure_technician"

    closure_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_order_closure.id"), primary_key=True
    )
    field_technician_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("field_technician.id"), primary_key=True
    )


class WorkOrderClosureTask(Base):
    """Tareas del tipo de trabajo que se tildaron al cerrar (E05-04)."""

    __tablename__ = "work_order_closure_task"

    closure_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_order_closure.id"), primary_key=True
    )
    task_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("task.id"), primary_key=True)


class WorkOrderClosurePhoto(Base):
    """Fotos del cierre, hasta 5 (E05-06). Cada archivo pertenece a un solo cierre."""

    __tablename__ = "work_order_closure_photo"

    closure_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_order_closure.id"), primary_key=True
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("stored_file.id"), primary_key=True, unique=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class WorkOrderCheckItem(TimestampedBase):
    """Paso del checklist copiado a la orden al generarla (E07-01, criterio 3).

    Se copia el nombre: si la oficina después edita o desactiva el paso, la orden conserva
    la lista con la que se generó.
    """

    __tablename__ = "work_order_check_item"
    __table_args__ = (
        Index("uq_work_order_check_item_position", "work_order_id", "position", unique=True),
    )

    work_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_order.id"), nullable=False, index=True
    )
    step_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("maintenance_check_step.id"), nullable=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class WorkOrderClosureCheck(Base):
    """Respuesta de la escuadrilla a un paso del checklist al cerrar (E07-06 y E07-08)."""

    __tablename__ = "work_order_closure_check"
    __table_args__ = (
        # No OK lleva observación; OK no lleva ni observación ni "requiere reparación".
        CheckConstraint(
            "(result = 'not_ok') = (observation IS NOT NULL)",
            name="ck_work_order_closure_check_observation",
        ),
        CheckConstraint(
            "result = 'not_ok' OR NOT requires_repair",
            name="ck_work_order_closure_check_repair",
        ),
    )

    closure_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_order_closure.id"), primary_key=True
    )
    check_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_order_check_item.id"), primary_key=True
    )
    result: Mapped[CheckResult] = mapped_column(
        Enum(CheckResult, name="check_result"), nullable=False
    )
    observation: Mapped[str | None] = mapped_column(Text, nullable=True)
    requires_repair: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )


class WorkOrderCancellation(TimestampedBase):
    """Cancelación de una orden por administración (E04-07). Una por orden: es final (R5)."""

    __tablename__ = "work_order_cancellation"
    __table_args__ = (
        Index(
            "uq_work_order_cancellation_work_order",
            "work_order_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        # El texto va solo con "Otro", y con "Otro" es obligatorio.
        CheckConstraint(
            "(reason = 'other') = (reason_text IS NOT NULL)",
            name="ck_work_order_cancellation_reason_text",
        ),
    )

    work_order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("work_order.id"), nullable=False)
    reason: Mapped[CancelReason] = mapped_column(
        Enum(CancelReason, name="cancel_reason"), nullable=False
    )
    reason_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cancelled_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    cancelled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class WorkOrderBilling(TimestampedBase):
    """Mano de obra de una orden terminada (E04-14), cargada a mano. Una por orden; se
    reemplaza al editar. Factura y cobro van en sus tablas (E04-09, E04-10)."""

    __tablename__ = "work_order_billing"
    __table_args__ = (
        Index(
            "uq_work_order_billing_work_order",
            "work_order_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint(
            "parts_amount >= 0 AND labor_amount >= 0", name="ck_work_order_billing_amounts"
        ),
    )

    work_order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("work_order.id"), nullable=False)
    parts_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    labor_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    updated_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), nullable=False)


class WorkOrderCharge(TimestampedBase):
    """Otro cargo de la orden con descripción e importe, además de la mano de obra
    (E04-11). Sacarlo es borrado lógico; cada cambio queda en la línea de tiempo."""

    __tablename__ = "work_order_charge"
    __table_args__ = (CheckConstraint("amount >= 0", name="ck_work_order_charge_amount"),)

    work_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_order.id"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), nullable=False)


class Invoice(TimestampedBase):
    """Factura registrada por administración (E04-09). Puede cubrir varias órdenes, por
    ejemplo las de un abonado (Gonza, 2026-11-10). La emite el sistema del cliente."""

    __tablename__ = "invoice"

    number: Mapped[str] = mapped_column(String(50), nullable=False)
    issued_on: Mapped[date] = mapped_column(Date, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), nullable=False)


class WorkOrderInvoice(TimestampedBase):
    """Qué factura cubre cada orden: una vigente por orden."""

    __tablename__ = "work_order_invoice"
    __table_args__ = (
        Index(
            "uq_work_order_invoice_work_order",
            "work_order_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    work_order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("work_order.id"), nullable=False)
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("invoice.id"), nullable=False, index=True
    )


class WorkOrderPayment(TimestampedBase):
    """Cobro de una orden facturada (E04-10): fecha y medio; el importe es el total de la
    orden. Anularlo no lo borra: queda con quién, cuándo y por qué."""

    __tablename__ = "work_order_payment"
    __table_args__ = (
        Index(
            "uq_work_order_payment_current",
            "work_order_id",
            unique=True,
            postgresql_where=text("voided_at IS NULL AND deleted_at IS NULL"),
        ),
        CheckConstraint(
            "(voided_at IS NULL) = (voided_by IS NULL AND void_reason IS NULL)",
            name="ck_work_order_payment_void",
        ),
    )

    work_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_order.id"), nullable=False, index=True
    )
    paid_on: Mapped[date] = mapped_column(Date, nullable=False)
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(PaymentMethod, name="payment_method"), nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"), nullable=True)
    void_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
