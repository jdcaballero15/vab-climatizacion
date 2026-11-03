from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.search import ClientSearchOut, EquipmentSearchOut, SearchOut
from app.db.repositories.search import SearchRepository
from app.services.clients import normalize_text

# Para elegir entre pocos; si no está, se sigue escribiendo.
RESULTS_PER_KIND = 10


async def search(session: AsyncSession, text: str, *, include_deleted: bool) -> SearchOut:
    """Clientes y equipos que coinciden con lo escrito (E03-06)."""
    query = normalize_text(text)
    repository = SearchRepository(session)
    clients = await repository.clients(
        query, include_deleted=include_deleted, limit=RESULTS_PER_KIND
    )
    equipment = await repository.equipment(
        query, include_deleted=include_deleted, limit=RESULTS_PER_KIND
    )
    return SearchOut(
        clients=[
            ClientSearchOut(
                id=client.id,
                number=client.number,
                name=client.name,
                address=address,
                deleted=client.deleted_at is not None,
            )
            for client, address in clients
        ],
        equipment=[
            EquipmentSearchOut(
                id=item.id,
                internal_code=item.internal_code,
                location_note=item.location_note,
                equipment_type_name=type_name,
                brand=item.brand,
                model=item.model,
                client_id=client.id,
                client_name=client.name,
                site_label=site_label,
                site_address=site_address,
                deleted=item.deleted_at is not None,
            )
            for item, type_name, client, site_label, site_address in equipment
        ],
    )
