import unicodedata
import uuid
from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.client import (
    ClientCreate,
    ClientSiteTechnicianOut,
    ClientUpdate,
    ContactCreate,
    ContactUpdate,
    SiteAdminOut,
    SiteCreate,
    SiteUpdate,
    site_map_url,
)
from app.db.models.client import Client, ClientContact, ClientSegment, ClientSite
from app.db.repositories.client import (
    ClientContactRepository,
    ClientRepository,
    ClientSiteRepository,
)
from app.db.repositories.equipment import EquipmentRepository

# Veces que se reintenta el alta si dos altas simultáneas toman el mismo número.
_NUMBER_ATTEMPTS = 3
# Por debajo de este largo, un nombre no se compara por contención ("Sol" no avisa por
# "Farmacia Del Sol"): daría avisos en casi todos los clientes.
_MIN_CONTAINED_LENGTH = 4


class ClientNotFoundError(Exception):
    """No existe un cliente activo con ese id."""


class ClientNumberAlreadyExistsError(Exception):
    """El número de cliente ya existe (también contra los dados de baja)."""


class ContactNotFoundError(Exception):
    """No existe un contacto activo con ese id en ese cliente."""


class SiteNotFoundError(Exception):
    """No existe un domicilio con ese id (o no es del cliente indicado)."""


class SiteOfAnotherClientError(Exception):
    """El domicilio elegido es de otro cliente."""


class SiteInactiveError(Exception):
    """El domicilio elegido está desactivado."""


class ContactWithoutDataError(Exception):
    """El contacto no tiene nombre, teléfono ni email."""


class MonthlyReportRequiresEmailError(Exception):
    """El contacto recibe el informe mensual pero no tiene email."""


async def create_client(
    session: AsyncSession, data: ClientCreate, *, number: str | None = None
) -> Client:
    """Da de alta un cliente. Sin número, el sistema asigna el siguiente de la serie.

    El número explícito lo usa la importación desde Persat (E11-01); la API no lo expone.
    """
    repo = ClientRepository(session)
    if number is not None and await repo.get_by_number(number) is not None:
        raise ClientNumberAlreadyExistsError

    for _ in range(_NUMBER_ATTEMPTS):
        assigned = number if number is not None else str((await repo.max_numeric_number() or 0) + 1)
        client = Client(number=assigned, **data.model_dump())
        session.add(client)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            if number is not None:
                raise ClientNumberAlreadyExistsError from None
            continue
        await session.refresh(client)
        return client
    raise ClientNumberAlreadyExistsError


async def list_clients(
    session: AsyncSession,
    *,
    segment: ClientSegment | None,
    search: str | None = None,
    limit: int,
    offset: int,
) -> tuple[Sequence[Client], int]:
    """search filtra por parte del nombre o por el número, sin mayúsculas ni acentos."""
    return await ClientRepository(session).list_page(
        segment=segment, search=_normalize(search or "") or None, limit=limit, offset=offset
    )


async def get_client(session: AsyncSession, client_id: uuid.UUID) -> Client:
    client = await ClientRepository(session).get(client_id)
    if client is None:
        raise ClientNotFoundError
    return client


async def update_client(session: AsyncSession, client_id: uuid.UUID, data: ClientUpdate) -> Client:
    client = await get_client(session, client_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(client, field, value)
    await session.commit()
    await session.refresh(client)
    return client


async def find_similar_clients(
    session: AsyncSession, name: str, *, exclude_id: uuid.UUID | None = None
) -> list[Client]:
    """Clientes con un nombre muy parecido: igual sin distinguir mayúsculas, acentos ni
    espacios de más, o uno contenido en el otro. Sirve para advertir, no para rechazar.

    Se compara en Python: son unos cientos de clientes y evita depender de extensiones.
    """
    target = _normalize(name)
    if not target:
        return []
    similar = []
    for client in await ClientRepository(session).list():
        if client.id == exclude_id:
            continue
        candidate = _normalize(client.name)
        if candidate == target or _contains(candidate, target) or _contains(target, candidate):
            similar.append(client)
    return sorted(similar, key=lambda c: (c.name, c.number))


def _normalize(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    without_accents = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(without_accents.split())


def _contains(text: str, part: str) -> bool:
    return len(part) >= _MIN_CONTAINED_LENGTH and part in text


async def list_contacts(session: AsyncSession, client_id: uuid.UUID) -> Sequence[ClientContact]:
    await get_client(session, client_id)
    return await ClientContactRepository(session).list_for_client(client_id)


async def create_contact(
    session: AsyncSession, client_id: uuid.UUID, data: ContactCreate
) -> ClientContact:
    await get_client(session, client_id)
    await _check_site_of_client(session, client_id, data.client_site_id)
    contact = ClientContact(client_id=client_id, **data.model_dump())
    _check_contact(contact)
    session.add(contact)
    await session.commit()
    await session.refresh(contact)
    return contact


async def update_contact(
    session: AsyncSession, client_id: uuid.UUID, contact_id: uuid.UUID, data: ContactUpdate
) -> ClientContact:
    await get_client(session, client_id)
    contact = await ClientContactRepository(session).get_for_client(client_id, contact_id)
    if contact is None:
        raise ContactNotFoundError
    changes = data.model_dump(exclude_unset=True)
    if changes.get("receives_monthly_report", False) is None:
        changes.pop("receives_monthly_report")
    if changes.get("client_site_id") is not None:
        await _check_site_of_client(session, client_id, changes["client_site_id"])
    for field, value in changes.items():
        setattr(contact, field, value)
    # Las reglas se chequean sobre el contacto ya modificado: un cambio parcial puede
    # dejarlo sin datos o sin el email que necesita el informe.
    try:
        _check_contact(contact)
    except (ContactWithoutDataError, MonthlyReportRequiresEmailError):
        await session.rollback()
        raise
    await session.commit()
    await session.refresh(contact)
    return contact


def _check_contact(contact: ClientContact) -> None:
    if not (contact.name or contact.phone or contact.email):
        raise ContactWithoutDataError
    if contact.receives_monthly_report and not contact.email:
        raise MonthlyReportRequiresEmailError


async def _check_site_of_client(
    session: AsyncSession, client_id: uuid.UUID, site_id: uuid.UUID | None
) -> None:
    if site_id is None:
        return
    site = await ClientSiteRepository(session).get(site_id)
    if site is None or site.client_id != client_id:
        raise SiteNotFoundError


async def check_active_site_of_client(
    session: AsyncSession, client_id: uuid.UUID, site_id: uuid.UUID
) -> ClientSite:
    """Domicilio elegido para un equipo o una orden: existe, es del cliente y está activo."""
    site = await ClientSiteRepository(session).get(site_id)
    if site is None:
        raise SiteNotFoundError
    if site.client_id != client_id:
        raise SiteOfAnotherClientError
    if not site.is_active:
        raise SiteInactiveError
    return site


async def list_sites(session: AsyncSession, client_id: uuid.UUID) -> list[SiteAdminOut]:
    await get_client(session, client_id)
    return await _with_equipment_count(
        session, await ClientSiteRepository(session).list_for_client(client_id)
    )


async def create_site(session: AsyncSession, client_id: uuid.UUID, data: SiteCreate) -> ClientSite:
    await get_client(session, client_id)
    site = ClientSite(client_id=client_id, **data.model_dump())
    session.add(site)
    await session.commit()
    await session.refresh(site)
    return site


async def site_admin_out(session: AsyncSession, site: ClientSite) -> SiteAdminOut:
    [out] = await _with_equipment_count(session, [site])
    return out


async def _with_equipment_count(
    session: AsyncSession, sites: Sequence[ClientSite]
) -> list[SiteAdminOut]:
    counts = await EquipmentRepository(session).count_by_site([site.id for site in sites])
    return [
        SiteAdminOut.model_validate(
            {
                "id": site.id,
                "client_id": site.client_id,
                "label": site.label,
                "address": site.address,
                "reference": site.reference,
                "is_active": site.is_active,
                "equipment_count": counts.get(site.id, 0),
            }
        )
        for site in sites
    ]


async def get_site(session: AsyncSession, site_id: uuid.UUID) -> ClientSite:
    site = await ClientSiteRepository(session).get(site_id)
    if site is None:
        raise SiteNotFoundError
    return site


async def update_site(session: AsyncSession, site_id: uuid.UUID, data: SiteUpdate) -> ClientSite:
    site = await get_site(session, site_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(site, field, value)
    await session.commit()
    await session.refresh(site)
    return site


async def get_site_for_technician(
    session: AsyncSession, site_id: uuid.UUID
) -> ClientSiteTechnicianOut:
    """Domicilio tal como lo ve el técnico en su orden (lo usa E05-02)."""
    site = await get_site(session, site_id)
    contacts = await ClientContactRepository(session).list_for_site(site_id)
    return ClientSiteTechnicianOut(
        address=site.address,
        reference=site.reference,
        map_url=site_map_url(site.address),
        contact_names=[c.name for c in contacts if c.name],
    )
