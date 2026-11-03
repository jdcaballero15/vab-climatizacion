from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import SessionDep, require_role
from app.api.schemas.search import SearchOut
from app.db.models.user import User, UserRole
from app.services import search as search_service

router = APIRouter(prefix="/admin/search", tags=["clientes"])

AdminOrOwner = Annotated[User, Depends(require_role(UserRole.admin, UserRole.owner))]


@router.get("", response_model=SearchOut)
async def search(
    session: SessionDep,
    _: AdminOrOwner,
    q: Annotated[str, Query(min_length=2, max_length=100)],
    include_deleted: bool = False,
) -> SearchOut:
    """Clientes y equipos por nombre, número, dirección, teléfono o código (E03-06)."""
    return await search_service.search(session, q, include_deleted=include_deleted)
