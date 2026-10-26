import uuid

from pydantic import BaseModel, ConfigDict, EmailStr

from app.api.schemas.catalog import CatalogName


class CrewCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: CatalogName
    app_user_id: uuid.UUID | None = None


class CrewUpdate(BaseModel):
    """Solo se cambian los campos enviados; app_user_id en null desasocia el usuario."""

    model_config = ConfigDict(extra="forbid")

    name: CatalogName | None = None
    is_active: bool | None = None
    app_user_id: uuid.UUID | None = None


class CrewUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: EmailStr
    # Si lo desactivaron en Usuarios, la pantalla lo marca (no se desasocia solo).
    is_active: bool


class CrewAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    is_active: bool
    app_user: CrewUserOut | None


class FieldTechnicianCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: CatalogName


class FieldTechnicianUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: CatalogName | None = None
    is_active: bool | None = None


class FieldTechnicianAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    is_active: bool
