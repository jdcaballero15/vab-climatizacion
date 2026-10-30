import uuid
from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import SessionDep, require_role
from app.api.schemas.client import (
    ClientAdminOut,
    ClientCreate,
    ClientPage,
    ClientSummaryOut,
    ClientUpdate,
    ContactAdminOut,
    ContactCreate,
    ContactUpdate,
    SiteAdminOut,
    SiteCreate,
    SiteUpdate,
)
from app.db.models.client import Client, ClientContact, ClientSegment
from app.db.models.user import User, UserRole
from app.services import clients as clients_service

router = APIRouter(prefix="/admin/clients", tags=["clientes"])
# Un domicilio se edita por su id, sin repetir el del cliente en la ruta.
sites_router = APIRouter(prefix="/admin/sites", tags=["clientes"])

# Solo administración gestiona clientes; dirección los ve en la ficha (E03-04).
AdminOnly = Annotated[User, Depends(require_role(UserRole.admin))]


@router.get("", response_model=ClientPage)
async def list_clients(
    session: SessionDep,
    _: AdminOnly,
    segment: ClientSegment | None = None,
    q: Annotated[str | None, Query(max_length=255)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ClientPage:
    items, total = await clients_service.list_clients(
        session, segment=segment, search=q, limit=limit, offset=offset
    )
    return ClientPage(
        items=[ClientSummaryOut.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=ClientAdminOut, status_code=status.HTTP_201_CREATED)
async def create_client(payload: ClientCreate, session: SessionDep, _: AdminOnly) -> Client:
    return await clients_service.create_client(session, payload)


# Va antes de /{client_id} para que "similar" no se tome como un id.
@router.get("/similar", response_model=list[ClientSummaryOut])
async def find_similar_clients(
    session: SessionDep,
    _: AdminOnly,
    name: Annotated[str, Query(max_length=255)],
    exclude_id: uuid.UUID | None = None,
) -> list[Client]:
    return await clients_service.find_similar_clients(session, name, exclude_id=exclude_id)


@router.get("/{client_id}", response_model=ClientAdminOut)
async def get_client(client_id: uuid.UUID, session: SessionDep, _: AdminOnly) -> Client:
    try:
        return await clients_service.get_client(session, client_id)
    except clients_service.ClientNotFoundError:
        raise _client_not_found() from None


@router.patch("/{client_id}", response_model=ClientAdminOut)
async def update_client(
    client_id: uuid.UUID, payload: ClientUpdate, session: SessionDep, _: AdminOnly
) -> Client:
    try:
        return await clients_service.update_client(session, client_id, payload)
    except clients_service.ClientNotFoundError:
        raise _client_not_found() from None


@router.get("/{client_id}/contacts", response_model=list[ContactAdminOut])
async def list_contacts(
    client_id: uuid.UUID, session: SessionDep, _: AdminOnly
) -> Sequence[ClientContact]:
    try:
        return await clients_service.list_contacts(session, client_id)
    except clients_service.ClientNotFoundError:
        raise _client_not_found() from None


@router.post(
    "/{client_id}/contacts", response_model=ContactAdminOut, status_code=status.HTTP_201_CREATED
)
async def create_contact(
    client_id: uuid.UUID, payload: ContactCreate, session: SessionDep, _: AdminOnly
) -> ClientContact:
    try:
        return await clients_service.create_contact(session, client_id, payload)
    except clients_service.ClientNotFoundError:
        raise _client_not_found() from None
    except clients_service.SiteNotFoundError:
        raise _site_not_found() from None
    except clients_service.ContactWithoutDataError:
        raise _contact_without_data() from None
    except clients_service.MonthlyReportRequiresEmailError:
        raise _report_requires_email() from None


@router.patch("/{client_id}/contacts/{contact_id}", response_model=ContactAdminOut)
async def update_contact(
    client_id: uuid.UUID,
    contact_id: uuid.UUID,
    payload: ContactUpdate,
    session: SessionDep,
    _: AdminOnly,
) -> ClientContact:
    try:
        return await clients_service.update_contact(session, client_id, contact_id, payload)
    except clients_service.ClientNotFoundError:
        raise _client_not_found() from None
    except clients_service.ContactNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "contact_not_found", "message": "No se encontró el contacto."},
        ) from None
    except clients_service.SiteNotFoundError:
        raise _site_not_found() from None
    except clients_service.ContactWithoutDataError:
        raise _contact_without_data() from None
    except clients_service.MonthlyReportRequiresEmailError:
        raise _report_requires_email() from None


@router.get("/{client_id}/sites", response_model=list[SiteAdminOut])
async def list_sites(client_id: uuid.UUID, session: SessionDep, _: AdminOnly) -> list[SiteAdminOut]:
    try:
        return await clients_service.list_sites(session, client_id)
    except clients_service.ClientNotFoundError:
        raise _client_not_found() from None


@router.post("/{client_id}/sites", response_model=SiteAdminOut, status_code=status.HTTP_201_CREATED)
async def create_site(
    client_id: uuid.UUID, payload: SiteCreate, session: SessionDep, _: AdminOnly
) -> SiteAdminOut:
    try:
        site = await clients_service.create_site(session, client_id, payload)
    except clients_service.ClientNotFoundError:
        raise _client_not_found() from None
    return await clients_service.site_admin_out(session, site)


@sites_router.get("/{site_id}", response_model=SiteAdminOut)
async def get_site(site_id: uuid.UUID, session: SessionDep, _: AdminOnly) -> SiteAdminOut:
    try:
        site = await clients_service.get_site(session, site_id)
    except clients_service.SiteNotFoundError:
        raise _site_not_found() from None
    return await clients_service.site_admin_out(session, site)


@sites_router.patch("/{site_id}", response_model=SiteAdminOut)
async def update_site(
    site_id: uuid.UUID, payload: SiteUpdate, session: SessionDep, _: AdminOnly
) -> SiteAdminOut:
    try:
        site = await clients_service.update_site(session, site_id, payload)
    except clients_service.SiteNotFoundError:
        raise _site_not_found() from None
    return await clients_service.site_admin_out(session, site)


def _client_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "client_not_found", "message": "No se encontró el cliente."},
    )


def _site_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "site_not_found", "message": "No se encontró el domicilio."},
    )


def _contact_without_data() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={
            "code": "contact_without_data",
            "message": "El contacto necesita al menos un nombre, un teléfono o un email.",
        },
    )


def _report_requires_email() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail={
            "code": "monthly_report_requires_email",
            "message": "Para recibir el informe mensual, el contacto necesita un email.",
        },
    )
