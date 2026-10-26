import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Sequence,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TimestampedBase
from app.domain.work_order import OrderKind, OrderSource, OrderStatus, WorkOrderEventType

ORDER_STATUS = Enum(OrderStatus, name="order_status")
WORK_ORDER_NUMBER_SEQ = Sequence("work_order_number_seq")

# varchar con CHECK y no un enum de Postgres: sumar un tipo de evento no obliga a migrar
# un enum, solo a reemplazar la restricción.
EVENT_TYPE_CHECK = "event_type IN ({})".format(
    ", ".join(f"'{event_type.value}'" for event_type in WorkOrderEventType)
)


class WorkOrder(TimestampedBase):
    """Orden de trabajo. Las fechas de negocio salen de sus eventos (ADR 0005)."""

    __tablename__ = "work_order"

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
