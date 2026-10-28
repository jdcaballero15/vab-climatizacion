import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Usos permitidos; cada uno define sus tipos en el servicio.
FilePurpose = Literal["closure_photo", "closure_signature"]


class UploadRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    purpose: FilePurpose
    content_type: str = Field(max_length=100)
    size_bytes: int = Field(gt=0)


class UploadOut(BaseModel):
    file_id: uuid.UUID
    # PUT a esta URL con el mismo Content-Type y el archivo como cuerpo.
    upload_url: str
    expires_in: int


class FileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    purpose: str
    content_type: str
    size_bytes: int
    confirmed_at: datetime | None


class DownloadOut(BaseModel):
    download_url: str
    expires_in: int
