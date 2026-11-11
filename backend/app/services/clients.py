import unicodedata
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import Select, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.client import (
    AuditEntryOut,
    ClientAdminOut,
    ClientCreate,
    ClientMergePreviewOut,
    ClientSiteTechnicianOut,
    ClientSummaryOut,
    ClientUpdate,
    ContactCreate,
    ContactUpdate,
    SiteAdminOut,
    SiteCreate,
    SiteUpdate,
    site_map_url,
)
from app.db.models.client import Client, ClientContact, ClientSegment, ClientSite
from app.db.models.equipment import Equipment
from app.db.models.user import User
from app.db.models.work_order import WorkOrder
from app.db.repositories.client import (
    ClientContactRepository,
    ClientRepository,
    ClientSiteRepository,
)
from app.db.repositories.equipment import EquipmentRepository
from app.domain.work_order import OPEN_STATUSES
from app.services import audit

# Veces que se reintenta el alta si dos altas simultáneas toman el mismo número.
_NUMBER_ATTEMPTS = 3
# Por debajo de este largo, un nombre no se compara por contención ("Sol" no avisa por
# "Farmacia Del Sol"): daría avisos en casi todos los clientes.
_MIN_CONTAINED_LENGTH = 4


# Lo que se muestra en la ficha del cliente: bajas, restauraciones y unificaciones.
CLIENT_TRAIL_ACTIONS = frozenset({"deactivated", "restored", "merged", "merged_in"})


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


class ClientHasOpenOrdersError(Exception):
    """El cliente tiene órdenes sin cerrar: no se da de baja (E03-07, criterio 4)."""

    def __init__(self, numbers: Sequence[int]) -> None:
        listed = ", ".join(f"N° {n}" for n in numbers)
        self.message = f"El cliente tiene órdenes abiertas: {listed}. Cerralas o cancelalas antes."
        super().__init__(self.message)


class ClientMergedError(Exception):
    """El cliente se unificó en otro: no se restaura (E03-08)."""


class ClientNotDeletedError(Exception):
    """El cliente no está dado de baja."""


class SameClientMergeError(Exception):
    """Se intentó unificar un cliente en sí mismo."""


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
    deleted: bool = False,
    limit: int,
    offset: int,
) -> tuple[Sequence[Client], int]:
    """search filtra por parte del nombre o por el número, sin mayúsculas ni acentos. Con
    deleted, solo los dados de baja (para restaurarlos, E03-07)."""
    return await ClientRepository(session).list_page(
        segment=segment,
        search=normalize_text(search or "") or None,
        deleted=deleted,
        limit=limit,
        offset=offset,
    )


async def get_client(
    session: AsyncSession, client_id: uuid.UUID, *, include_deleted: bool = False
) -> Client:
    """Para leer historial se piden también los dados de baja: conservan todo (E03-07)."""
    client = await ClientRepository(session).get(client_id, include_deleted=include_deleted)
    if client is None:
        raise ClientNotFoundError
    return client


async def client_admin_out(session: AsyncSession, client: Client) -> ClientAdminOut:
    merged_into = (
        await get_client(session, client.merged_into_id, include_deleted=True)
        if client.merged_into_id is not None
        else None
    )
    out = ClientAdminOut.model_validate(client)
    out.merged_into = ClientSummaryOut.model_validate(merged_into) if merged_into else None
    return out


async def audit_trail(session: AsyncSession, client_id: uuid.UUID) -> list[AuditEntryOut]:
    await get_client(session, client_id, include_deleted=True)
    return [
        AuditEntryOut(
            action=event.action,
            actor_name=name,
            occurred_at=event.occurred_at,
            # Las diferencias en JSON quedan para la pantalla de auditoría (E12-01).
            detail=event.detail if event.action == "merged_in" else None,
        )
        for event, name in await audit.events_for(session, "client", client_id)
        if event.action in CLIENT_TRAIL_ACTIONS
    ]


async def deactivate_client(session: AsyncSession, client_id: uuid.UUID, actor: User) -> Client:
    """Baja lógica: deja de ofrecerse para órdenes nuevas y conserva su historial."""
    client = await get_client(session, client_id)
    open_numbers = (
        await session.scalars(
            select(WorkOrder.number)
            .where(
                WorkOrder.client_id == client.id,
                WorkOrder.status.in_(OPEN_STATUSES),
                WorkOrder.deleted_at.is_(None),
            )
            .order_by(WorkOrder.number)
        )
    ).all()
    if open_numbers:
        raise ClientHasOpenOrdersError(open_numbers)
    client.deleted_at = datetime.now(UTC)
    await session.commit()
    await session.refresh(client)
    return client


async def restore_client(session: AsyncSession, client_id: uuid.UUID, actor: User) -> Client:
    client = await get_client(session, client_id, include_deleted=True)
    if client.deleted_at is None:
        raise ClientNotDeletedError
    if client.merged_into_id is not None:
        raise ClientMergedError
    client.deleted_at = None
    await session.commit()
    await session.refresh(client)
    return client


async def merge_preview(
    session: AsyncSession, source_id: uuid.UUID, target_id: uuid.UUID
) -> ClientMergePreviewOut:
    """Qué se va a mover del que se va al que queda, para confirmar (E03-08, criterio 4)."""
    source, target = await _merge_pair(session, source_id, target_id)

    async def count(stmt: Select[int]) -> int:
        return int(await session.scalar(stmt) or 0)

    return ClientMergePreviewOut(
        source_id=source.id,
        source_name=source.name,
        source_number=source.number,
        target_id=target.id,
        target_name=target.name,
        target_number=target.number,
        sites=await count(
            select(func.count()).where(
                ClientSite.client_id == source.id, ClientSite.deleted_at.is_(None)
            )
        ),
        contacts=await count(
            select(func.count()).where(
                ClientContact.client_id == source.id, ClientContact.deleted_at.is_(None)
            )
        ),
        equipment=await count(
            select(func.count())
            .select_from(Equipment)
            .join(ClientSite, ClientSite.id == Equipment.client_site_id)
            .where(ClientSite.client_id == source.id, Equipment.deleted_at.is_(None))
        ),
        orders=await count(
            select(func.count()).where(
                WorkOrder.client_id == source.id, WorkOrder.deleted_at.is_(None)
            )
        ),
    )


async def merge_clients(
    session: AsyncSession, source_id: uuid.UUID, target_id: uuid.UUID, actor: User
) -> ClientMergePreviewOut:
    """Pasa domicilios (con sus equipos y planes), contactos y órdenes del que se va al que
    queda, y da de baja al que se va. Los equipos conservan su código (D-002)."""
    preview = await merge_preview(session, source_id, target_id)
    for model in (ClientSite, ClientContact, WorkOrder):
        await session.execute(
            update(model).where(model.client_id == source_id).values(client_id=target_id)
        )
    source = await get_client(session, source_id)
    source.deleted_at = datetime.now(UTC)
    source.merged_into_id = target_id
    audit.record(
        session,
        "client",
        target_id,
        "merged_in",
        actor,
        f"Recibió el cliente N° {preview.source_number} ({preview.source_name})",
    )
    await session.commit()
    return preview


async def _merge_pair(
    session: AsyncSession, source_id: uuid.UUID, target_id: uuid.UUID
) -> tuple[Client, Client]:
    if source_id == target_id:
        raise SameClientMergeError
    return await get_client(session, source_id), await get_client(session, target_id)


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
    target = normalize_text(name)
    if not target:
        return []
    similar = []
    for client in await ClientRepository(session).list():
        if client.id == exclude_id:
            continue
        candidate = normalize_text(client.name)
        if candidate == target or _contains(candidate, target) or _contains(target, candidate):
            similar.append(client)
    return sorted(similar, key=lambda c: (c.name, c.number))


def normalize_text(value: str) -> str:
    """Sin mayúsculas, acentos ni espacios de más: como se compara al buscar."""
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
