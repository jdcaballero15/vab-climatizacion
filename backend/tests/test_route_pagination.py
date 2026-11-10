"""E12-05: los listados de la API están paginados con tope y orden estable.

Un listado nuevo que devuelve un arreglo sin paginar hace fallar este test, salvo que
esté abajo con el motivo: catálogos y listas que por naturaleza son chicos.
"""

import typing

from fastapi.routing import APIRoute

from app.main import app
from tests.test_route_authorization import _api_routes

MAX_PAGE_SIZE = 200
# Sin paginar a propósito: el motivo al lado. Ante la duda, paginar.
UNPAGINATED = {
    # Catálogos y equipo de trabajo: decenas de registros, se eligen de una lista.
    "/admin/users": "usuarios de la empresa",
    "/admin/work-types": "catálogo",
    "/admin/work-types/{work_type_id}/tasks": "tareas de un tipo de trabajo",
    "/admin/equipment-types": "catálogo",
    "/admin/failures": "catálogo",
    "/admin/repairs": "catálogo",
    "/admin/parts": "catálogo de materiales (cientos, filtrado en pantalla)",
    "/admin/crews": "escuadrillas",
    "/admin/field-technicians": "técnicos de campo",
    "/admin/maintenance/check-steps": "pasos del checklist",
    # De un solo cliente: sus domicilios, contactos y equipos son pocos.
    "/admin/clients/{client_id}/contacts": "de un cliente",
    "/admin/clients/{client_id}/sites": "de un cliente",
    "/admin/clients/{client_id}/equipment": "de un cliente",
    "/admin/clients/{client_id}/audit": "bajas y unificaciones de un cliente",
    # Textos de "Otro" agrupados: los distintos, que se revisan y se van sacando.
    "/admin/other-texts": "textos de Otro para revisar",
    # Sugerencias al escribir: el servicio ya devuelve pocas.
    "/admin/clients/similar": "sugerencias, con tope en el servicio",
    # Un plan por equipo con abono: cientos como mucho; se revisa si crece.
    "/admin/maintenance/plans": "planes de mantenimiento",
}


def _list_routes() -> list[APIRoute]:
    return [
        route
        for route in _api_routes(app.routes)
        if "GET" in route.methods and typing.get_origin(route.response_model) is list
    ]


def _page_routes() -> list[APIRoute]:
    return [
        route
        for route in _api_routes(app.routes)
        if "GET" in route.methods
        and hasattr(route.response_model, "model_fields")
        and {"items", "total", "limit", "offset"} <= set(route.response_model.model_fields)
    ]


def test_listados_sin_paginar_estan_justificados() -> None:
    sin_paginar = {route.path for route in _list_routes()}
    assert sin_paginar - set(UNPAGINATED) == set(), "Paginá el listado o justificá la excepción"


def test_las_excepciones_siguen_existiendo() -> None:
    assert set(UNPAGINATED) - {route.path for route in _list_routes()} == set()


def test_las_paginas_tienen_tope() -> None:
    for route in _page_routes():
        limit = next(
            (param for param in route.dependant.query_params if param.name == "limit"), None
        )
        assert limit is not None, f"{route.path} no tiene limit"
        tope = next(
            (getattr(m, "le", None) for m in limit.field_info.metadata if hasattr(m, "le")), None
        )
        assert tope is not None and tope <= MAX_PAGE_SIZE, f"{route.path}: limit sin tope"
        assert any(param.name == "offset" for param in route.dependant.query_params)
