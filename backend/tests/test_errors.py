"""E12-03: errores uniformes y en español."""

import logging
from typing import Annotated, Literal

import pytest
from fastapi import APIRouter, Query
from httpx import ASGITransport, AsyncClient

from app.core.errors import UNEXPECTED_MESSAGE
from app.main import create_app


# Criterio 1: {code, message} y el detalle por campo, en español.
async def test_validacion_con_campo_y_mensaje_en_espanol() -> None:
    app = create_app()
    router = APIRouter()

    @router.get("/prueba")
    async def prueba(
        status: Literal["pending", "done"], limit: Annotated[int, Query(ge=1)] = 50
    ) -> None:
        return None

    app.include_router(router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/prueba?status=archivada&limit=0")

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["code"] == "validation_error"
    assert detail["message"].startswith("Revisá los datos: ")
    assert detail["field"] == "status"
    campos = {f["field"]: f["message"] for f in detail["fields"]}
    assert campos["status"] == "No es una opción válida."
    assert campos["limit"] == "Tiene que ser mayor o igual a 1."


# Criterios 2 y 3: un error inesperado da un mensaje genérico; el detalle va solo al log.
async def test_error_inesperado_es_generico_y_va_al_log(caplog: pytest.LogCaptureFixture) -> None:
    app = create_app()
    router = APIRouter()

    @router.get("/boom")
    async def boom() -> None:
        raise RuntimeError("detalle interno con DNI 12345678")

    app.include_router(router)
    caplog.set_level(logging.ERROR, logger="app.errors")
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {"detail": {"code": "internal_error", "message": UNEXPECTED_MESSAGE}}
    assert "12345678" not in response.text
    assert "GET /boom" in caplog.text
