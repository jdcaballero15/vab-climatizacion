import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from app.api.deps import SessionDep, StorageDep, require_role
from app.db.models.document import DocumentKind
from app.db.models.user import User, UserRole
from app.services import documents as documents_service

router = APIRouter(tags=["comprobantes e informes"])

AdminOnly = Annotated[User, Depends(require_role(UserRole.admin))]
AdminOrOwner = Annotated[User, Depends(require_role(UserRole.admin, UserRole.owner))]


class DocumentLinkOut(BaseModel):
    """URL firmada del PDF guardado en el bucket; vence como las de fotos y firmas."""

    url: str


@router.post("/admin/orders/{order_id}/documents/{kind}", response_model=DocumentLinkOut)
async def get_receipt(
    order_id: uuid.UUID,
    kind: DocumentKind,
    session: SessionDep,
    storage: StorageDep,
    admin: AdminOnly,
) -> DocumentLinkOut:
    """Comprobante de retiro o devolución (E09-01, E09-02). La primera vez se arma y se
    guarda; después devuelve el mismo archivo. Es POST porque puede crearlo."""
    try:
        url = await documents_service.receipt_url(session, storage, order_id, kind, admin)
    except documents_service.OrderNotFoundError:
        raise _error(404, "order_not_found", "No se encontró la orden.") from None
    except documents_service.StageNotDoneError as exc:
        raise _error(409, exc.code, exc.message) from None
    return DocumentLinkOut(url=url)


@router.get(
    "/admin/clients/{client_id}/monthly-report",
    response_class=Response,
    responses={200: {"content": {"application/pdf": {}}}},
)
async def get_monthly_report(
    client_id: uuid.UUID,
    session: SessionDep,
    _: AdminOrOwner,
    year: Annotated[int, Query(ge=2020, le=2100)],
    month: Annotated[int, Query(ge=1, le=12)],
) -> Response:
    """Informe mensual del cliente en PDF, sin precios (E09-04)."""
    try:
        content = await documents_service.monthly_report(session, client_id, year, month)
    except documents_service.ClientNotFoundError:
        raise _error(404, "client_not_found", "No se encontró el cliente.") from None
    except documents_service.EmptyReportError as exc:
        raise _error(409, exc.code, exc.message) from None
    filename = f"informe-{year}-{month:02d}.pdf"
    return Response(
        content,
        media_type=documents_service.PDF,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})
