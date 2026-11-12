from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TimestampedBase


class ImportBatch(TimestampedBase):
    """Una importación confirmada (E11-05): qué se importó, cuándo, quién la corrió y
    cuánto creó. Lo creado lleva el lote en su referencia (legacy_reference.batch_id) para
    poder deshacerlo entero."""

    __tablename__ = "import_batch"

    source: Mapped[str] = mapped_column(String(50), nullable=False, default="persat")
    # Lo corre una persona desde una máquina con los archivos (no hay usuario de la app).
    run_by: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # "clientes: 632, equipos: 532, órdenes: 1743": para leerlo, no para calcular.
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    undone_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
