from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session

router = APIRouter(tags=["salud"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/health")
async def health() -> dict[str, str]:
    """Chequeo de vida para el balanceador del hosting y para CI."""
    return {"status": "ok"}


@router.get("/health/ready")
async def ready(response: Response, session: SessionDep) -> dict[str, str]:
    """Chequeo de readiness: confirma que la base responde."""
    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "database": "down"}
    return {"status": "ready", "database": "ok"}
