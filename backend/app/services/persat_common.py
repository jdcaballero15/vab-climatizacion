"""Lo común a la importación de Persat: errores, problemas a informar y referencias."""

import uuid
from contextvars import ContextVar
from dataclasses import dataclass

from app.db.models.legacy_reference import LegacyReference

SOURCE = "persat"

# El lote de la importación en curso (E11-05): cada referencia creada lo lleva.
current_batch: ContextVar[uuid.UUID | None] = ContextVar("persat_batch", default=None)


class PersatFileError(Exception):
    """El archivo no se puede leer o no tiene las columnas de la exportación de Persat."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class Issue:
    """Una fila del archivo con algo que informar. Sin nombres ni datos personales."""

    row: int
    ref: str
    reason: str


def reference(entity: str, entity_id: uuid.UUID, legacy_id: str) -> LegacyReference:
    return LegacyReference(
        entity=entity,
        entity_id=entity_id,
        source=SOURCE,
        legacy_id=legacy_id,
        batch_id=current_batch.get(),
    )
