"""Archivos en el bucket con URLs firmadas (E00-09)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.storage import ObjectStorage
from app.db.models.stored_file import StoredFile
from app.db.models.user import User, UserRole
from app.db.repositories.stored_file import StoredFileRepository

# Prefijo de la clave y tipos aceptados por uso. La clave no lleva datos personales.
_PURPOSES: dict[str, tuple[str, frozenset[str]]] = {
    "closure_photo": ("closures/photos", frozenset({"image/jpeg", "image/png", "image/webp"})),
    # La firma la dibuja la app en un lienzo: siempre PNG (E05-07).
    "closure_signature": ("closures/signatures", frozenset({"image/png"})),
}


class FileRejectedError(Exception):
    """El archivo no se acepta (tipo, tamaño o subida que no coincide). Lleva el campo."""

    def __init__(self, code: str, field: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.field = field
        self.message = message


class FileNotFoundForUserError(Exception):
    """No existe, o el usuario no tiene por qué saber que existe."""


async def request_upload(
    session: AsyncSession,
    storage: ObjectStorage,
    user: User,
    purpose: str,
    content_type: str,
    size_bytes: int,
) -> tuple[StoredFile, str]:
    settings = get_settings()
    prefix, purpose_types = _PURPOSES[purpose]
    if content_type not in purpose_types or content_type not in settings.upload_allowed_type_list:
        raise FileRejectedError(
            "file_type_not_allowed", "content_type", "Ese tipo de archivo no se acepta."
        )
    if size_bytes > settings.upload_max_bytes:
        max_mb = settings.upload_max_bytes // (1024 * 1024)
        raise FileRejectedError(
            "file_too_large", "size_bytes", f"El archivo supera el máximo de {max_mb} MB."
        )

    file = StoredFile(
        purpose=purpose,
        object_key=f"{prefix}/{uuid.uuid4()}",
        content_type=content_type,
        size_bytes=size_bytes,
        uploaded_by=user.id,
    )
    session.add(file)
    await session.commit()
    return file, storage.upload_url(file.object_key, content_type, size_bytes)


async def confirm_upload(
    session: AsyncSession, storage: ObjectStorage, user: User, file_id: uuid.UUID
) -> StoredFile:
    """Marca el archivo como disponible si el bucket tiene lo declarado. Idempotente."""
    file = await StoredFileRepository(session).get(file_id)
    if file is None or file.uploaded_by != user.id:
        raise FileNotFoundForUserError
    if file.confirmed_at is not None:
        return file

    stored = await storage.head(file.object_key)
    if stored is None:
        raise FileRejectedError(
            "upload_missing", "file_id", "El archivo no llegó. Volvé a intentar la subida."
        )
    if stored.size_bytes != file.size_bytes or stored.content_type != file.content_type:
        raise FileRejectedError(
            "upload_mismatch", "file_id", "El archivo subido no coincide con el pedido."
        )

    file.confirmed_at = datetime.now(UTC)
    await session.commit()
    return file


async def get_downloadable(session: AsyncSession, user: User, file_id: uuid.UUID) -> StoredFile:
    """La administración ve cualquier archivo; el técnico, solo los que subió."""
    file = await StoredFileRepository(session).get(file_id)
    if file is None or file.confirmed_at is None:
        raise FileNotFoundForUserError
    if user.role == UserRole.technician and file.uploaded_by != user.id:
        raise FileNotFoundForUserError
    return file
