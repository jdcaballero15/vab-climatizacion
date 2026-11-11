from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import SessionDep, require_role
from app.db.models.user import User, UserRole
from app.services import catalog_csv as csv_service
from app.services.catalog_csv import Catalog

router = APIRouter(prefix="/admin/catalog-csv", tags=["catálogos"])

AdminOnly = Annotated[User, Depends(require_role(UserRole.admin))]


class CsvUpload(BaseModel):
    """El contenido del CSV como texto (lo lee el navegador)."""

    model_config = ConfigDict(extra="forbid")

    content: Annotated[str, Field(max_length=2_000_000)]


class RowOut(BaseModel):
    row: int
    name: str
    detail: str


class CsvPreviewOut(BaseModel):
    creates: list[RowOut]
    changes: list[RowOut]
    errors: list[RowOut]
    unchanged: int
    applied: bool


@router.get(
    "/{catalog}",
    response_class=Response,
    responses={200: {"content": {"text/csv": {}}}},
)
async def export_catalog(catalog: Catalog, session: SessionDep, _: AdminOnly) -> Response:
    """El catálogo con las mismas columnas que acepta la importación (E02-08, criterio 3)."""
    content = await csv_service.export_csv(session, catalog)
    return Response(
        content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{catalog}.csv"'},
    )


@router.post("/{catalog}/preview", response_model=CsvPreviewOut)
async def preview_catalog(
    catalog: Catalog, payload: CsvUpload, session: SessionDep, _: AdminOnly
) -> CsvPreviewOut:
    """Altas, cambios y errores con su fila, sin aplicar nada (criterio 1)."""
    try:
        result = await csv_service.preview(session, catalog, payload.content)
    except csv_service.CsvFormatError as exc:
        raise _bad_file(exc.message) from None
    return _out(result, applied=False)


@router.post("/{catalog}/apply", response_model=CsvPreviewOut)
async def apply_catalog(
    catalog: Catalog, payload: CsvUpload, session: SessionDep, _: AdminOnly
) -> CsvPreviewOut:
    """Aplica todo junto; con algún error no aplica nada (criterio 2)."""
    try:
        result = await csv_service.apply(session, catalog, payload.content)
    except csv_service.CsvFormatError as exc:
        raise _bad_file(exc.message) from None
    return _out(result, applied=not result.errors)


def _out(result: csv_service.Preview, *, applied: bool) -> CsvPreviewOut:
    def rows(items: list[csv_service.RowChange]) -> list[RowOut]:
        return [RowOut(row=i.row, name=i.name, detail=i.detail) for i in items]

    return CsvPreviewOut(
        creates=rows(result.creates),
        changes=rows(result.changes),
        errors=rows(result.errors),
        unchanged=result.unchanged,
        applied=applied,
    )


def _bad_file(message: str) -> HTTPException:
    return HTTPException(status_code=422, detail={"code": "invalid_csv", "message": message})
