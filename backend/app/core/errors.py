"""Errores uniformes y en español (E12-03).

Toda respuesta de error lleva `detail` con `code` y `message`; los de validación suman el
campo (`field`, el primero) y la lista `fields`. Un error inesperado devuelve un mensaje
genérico: el detalle técnico va solo al log, sin datos del pedido.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("app.errors")

UNEXPECTED_MESSAGE = (
    "Ocurrió un error inesperado. Volvé a intentar; si sigue pasando, avisá a administración."
)

# Mensajes por tipo de error de pydantic. Los que llevan límite lo toman del contexto.
_MESSAGES = {
    "missing": "Falta este dato.",
    "extra_forbidden": "Este dato no se acepta.",
    "string_too_long": "Es demasiado largo (máximo {max_length} caracteres).",
    "string_too_short": "Es demasiado corto.",
    "too_short": "Falta al menos un elemento.",
    "too_long": "Tiene demasiados elementos (máximo {max_length}).",
    "greater_than": "Tiene que ser mayor que {gt}.",
    "greater_than_equal": "Tiene que ser mayor o igual a {ge}.",
    "less_than": "Tiene que ser menor que {lt}.",
    "less_than_equal": "Tiene que ser menor o igual a {le}.",
    "decimal_max_places": "Tiene demasiados decimales (máximo {decimal_places}).",
    "decimal_max_digits": "Es un número demasiado grande.",
    "uuid_parsing": "No es un identificador válido.",
    "date_parsing": "No es una fecha válida.",
    "date_from_datetime_parsing": "No es una fecha válida.",
    "datetime_parsing": "No es una fecha y hora válidas.",
    "value_error": "{error}",
    "enum": "No es una opción válida.",
    "literal_error": "No es una opción válida.",
}


def _field(loc: tuple[Any, ...]) -> str:
    """El campo sin el lugar del pedido ("body", "query"): `photo_ids`, `parts.0.quantity`."""
    parts = [str(part) for part in loc if part not in ("body", "query", "path", "header")]
    return ".".join(parts)


def _message(error: dict[str, Any]) -> str:
    template = _MESSAGES.get(error.get("type", ""), "No es un valor válido.")
    context = error.get("ctx") or {}
    if error.get("type") == "value_error":
        # Los validadores propios ya escriben en español; pydantic les antepone esto.
        return str(error.get("msg", "")).removeprefix("Value error, ")
    try:
        return template.format(**context)
    except (KeyError, IndexError):
        return "No es un valor válido."


async def _validation_error(request: Request, exc: Exception) -> JSONResponse:
    errors = exc.errors() if isinstance(exc, RequestValidationError) else []
    fields = [{"field": _field(tuple(e["loc"])), "message": _message(e)} for e in errors]
    first = fields[0] if fields else {"field": "", "message": "Revisá los datos."}
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "code": "validation_error",
                "message": f"Revisá los datos: {first['message']}",
                "field": first["field"],
                "fields": fields,
            }
        },
    )


async def _unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    # Solo método y ruta: nada del cuerpo ni de la consulta (pueden tener datos personales).
    logger.exception("Error inesperado en %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": {"code": "internal_error", "message": UNEXPECTED_MESSAGE}},
    )


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(Exception, _unexpected_error)
