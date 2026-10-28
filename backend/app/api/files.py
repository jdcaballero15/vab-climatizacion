import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep, StorageDep, require_role
from app.api.schemas.files import DownloadOut, FileOut, UploadOut, UploadRequest
from app.core.config import get_settings
from app.db.models.stored_file import StoredFile
from app.db.models.user import User, UserRole
from app.services import files as files_service

router = APIRouter(prefix="/files", tags=["archivos"])

AnyRole = Annotated[
    User, Depends(require_role(UserRole.admin, UserRole.technician, UserRole.owner))
]


@router.post("", response_model=UploadOut, status_code=status.HTTP_201_CREATED)
async def request_upload(
    payload: UploadRequest, session: SessionDep, storage: StorageDep, user: AnyRole
) -> UploadOut:
    try:
        file, url = await files_service.request_upload(
            session, storage, user, payload.purpose, payload.content_type, payload.size_bytes
        )
    except files_service.FileRejectedError as exc:
        raise _rejected(exc) from None
    return UploadOut(
        file_id=file.id, upload_url=url, expires_in=get_settings().signed_url_ttl_seconds
    )


@router.post("/{file_id}/confirm", response_model=FileOut)
async def confirm_upload(
    file_id: uuid.UUID, session: SessionDep, storage: StorageDep, user: AnyRole
) -> StoredFile:
    try:
        return await files_service.confirm_upload(session, storage, user, file_id)
    except files_service.FileNotFoundForUserError:
        raise _not_found() from None
    except files_service.FileRejectedError as exc:
        raise _rejected(exc) from None


@router.get("/{file_id}/download", response_model=DownloadOut)
async def download(
    file_id: uuid.UUID, session: SessionDep, storage: StorageDep, user: AnyRole
) -> DownloadOut:
    try:
        file = await files_service.get_downloadable(session, user, file_id)
    except files_service.FileNotFoundForUserError:
        raise _not_found() from None
    return DownloadOut(
        download_url=storage.download_url(file.object_key),
        expires_in=get_settings().signed_url_ttl_seconds,
    )


def _rejected(exc: files_service.FileRejectedError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail={"code": exc.code, "message": exc.message, "field": exc.field},
    )


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "file_not_found", "message": "El archivo no existe."},
    )
