import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TimestampedBase


class StockLocationKind(StrEnum):
    warehouse = "warehouse"
    truck = "truck"


class StockMovementKind(StrEnum):
    receipt = "receipt"
    transfer = "transfer"
    usage = "usage"
    adjustment = "adjustment"


class StockLocation(TimestampedBase):
    """Depósito o camioneta (E08-01). Cada escuadrilla anda siempre en la misma camioneta
    (D-013): la camioneta lleva la escuadrilla y de ahí se descuentan sus usos."""

    __tablename__ = "stock_location"
    __table_args__ = (
        CheckConstraint(
            "kind = 'truck' OR crew_id IS NULL", name="ck_stock_location_crew_only_truck"
        ),
        # Una camioneta activa por escuadrilla.
        Index(
            "uq_stock_location_crew",
            "crew_id",
            unique=True,
            postgresql_where=text("crew_id IS NOT NULL AND is_active AND deleted_at IS NULL"),
        ),
    )

    kind: Mapped[StockLocationKind] = mapped_column(
        Enum(StockLocationKind, name="stock_location_kind"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    crew_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("crew.id"), nullable=True)
    # Con movimientos no se borra: se desactiva (criterio 3).
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class StockMovement(TimestampedBase):
    """Movimiento de stock (regla 6: el saldo es la suma de movimientos, nunca se edita).

    quantity siempre positiva: sale de from_location_id y entra en to_location_id. Un
    ingreso solo tiene destino; un uso solo origen; un ajuste uno de los dos según el signo.
    """

    __tablename__ = "stock_movement"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_stock_movement_quantity"),
        CheckConstraint(
            "from_location_id IS NOT NULL OR to_location_id IS NOT NULL",
            name="ck_stock_movement_location",
        ),
        CheckConstraint(
            "kind <> 'adjustment' OR reason IS NOT NULL", name="ck_stock_movement_reason"
        ),
        # El uso de un material del cierre descuenta una sola vez (E08-04, criterio 2).
        Index(
            "uq_stock_movement_part_usage",
            "part_usage_id",
            unique=True,
            postgresql_where=text("part_usage_id IS NOT NULL"),
        ),
    )

    kind: Mapped[StockMovementKind] = mapped_column(
        Enum(StockMovementKind, name="stock_movement_kind"), nullable=False
    )
    part_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("part.id"), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    from_location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stock_location.id"), nullable=True, index=True
    )
    to_location_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("stock_location.id"), nullable=True, index=True
    )
    work_order_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("work_order.id"), nullable=True
    )
    part_usage_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("part_usage.id"), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
