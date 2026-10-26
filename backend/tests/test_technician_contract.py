import importlib
import pkgutil
import typing

from fastapi.routing import APIRoute
from pydantic import BaseModel

import app
from app.core.sensitive_fields import FORBIDDEN_TECHNICIAN_FIELDS
from app.main import app as fastapi_app

# E00-04: el tecnico nunca ve precios, mano de obra ni historial (ADR 0006).
# Este test recorre los esquemas del tecnico y falla si aparece un campo prohibido.


def _import_app_modules() -> None:
    """Importa todos los submodulos de app para que los esquemas se registren."""
    for module in pkgutil.walk_packages(app.__path__, prefix=f"{app.__name__}."):
        importlib.import_module(module.name)


def _is_model(obj: object) -> bool:
    return isinstance(obj, type) and issubclass(obj, BaseModel)


def _models_in_annotation(annotation: object) -> list[type[BaseModel]]:
    """Extrae los modelos Pydantic de una anotacion (list[X], X | None, etc.)."""
    found: list[type[BaseModel]] = []
    if _is_model(annotation):
        found.append(annotation)  # type: ignore[arg-type]
    for arg in typing.get_args(annotation):
        found.extend(_models_in_annotation(arg))
    return found


def _field_names(model: type[BaseModel], seen: set[type[BaseModel]] | None = None) -> set[str]:
    """Nombres de todos los campos del modelo, a cualquier profundidad."""
    seen = set() if seen is None else seen
    names: set[str] = set()
    if model in seen:
        return names
    seen.add(model)
    for field_name, field in model.model_fields.items():
        names.add(field_name)
        for nested in _models_in_annotation(field.annotation):
            names |= _field_names(nested, seen)
    return names


def _forbidden_in(model: type[BaseModel]) -> set[str]:
    return _field_names(model) & FORBIDDEN_TECHNICIAN_FIELDS


def _all_model_subclasses() -> set[type[BaseModel]]:
    result: set[type[BaseModel]] = set()
    stack = list(BaseModel.__subclasses__())
    while stack:
        cls = stack.pop()
        if cls in result:
            continue
        result.add(cls)
        stack.extend(cls.__subclasses__())
    return result


def _technician_schemas() -> list[type[BaseModel]]:
    _import_app_modules()
    return [
        cls
        for cls in _all_model_subclasses()
        if cls.__name__.endswith("TechnicianOut") and cls.__module__.startswith("app.")
    ]


def _tech_routes() -> list[APIRoute]:
    return [
        route
        for route in fastapi_app.routes
        if isinstance(route, APIRoute) and route.path.startswith("/tech/")
    ]


def _tech_error_models() -> list[type[BaseModel]]:
    models: list[type[BaseModel]] = []
    for route in _tech_routes():
        for response in route.responses.values():
            model = response.get("model") if isinstance(response, dict) else None
            if model is not None:
                models.extend(_models_in_annotation(model))
    return models


# Criterios 1 y 2: ningun esquema del tecnico expone un campo prohibido, a cualquier
# profundidad. La lista vive en un solo archivo (app/core/sensitive_fields.py).
def test_technician_schemas_have_no_forbidden_fields() -> None:
    offenders = {
        schema.__name__: sorted(_forbidden_in(schema))
        for schema in _technician_schemas()
        if _forbidden_in(schema)
    }
    assert offenders == {}, f"Esquemas de tecnico con campos prohibidos: {offenders}"


# Criterio 3: toda ruta bajo /tech/ devuelve un esquema *TechnicianOut.
def test_tech_routes_return_technician_schema() -> None:
    for route in _tech_routes():
        models = _models_in_annotation(route.response_model)
        assert models, f"La ruta {route.path} no declara esquema de respuesta"
        for model in models:
            assert model.__name__.endswith("TechnicianOut"), (
                f"La ruta {route.path} devuelve {model.__name__}, que no es un *TechnicianOut"
            )


# Nota del ADR: los esquemas de error del tecnico tampoco filtran datos prohibidos.
def test_tech_error_schemas_have_no_forbidden_fields() -> None:
    offenders = {
        model.__name__: sorted(_forbidden_in(model))
        for model in _tech_error_models()
        if _forbidden_in(model)
    }
    assert offenders == {}, f"Esquemas de error con campos prohibidos: {offenders}"


# El detector atrapa un campo prohibido anidado (si no, el contrato seria un no-op).
class _NestedTechnicianOut(BaseModel):
    note: str
    unit_price: float


class _OrderTechnicianOut(BaseModel):
    title: str
    nested: _NestedTechnicianOut


class _CleanTechnicianOut(BaseModel):
    title: str
    status: str


def test_scanner_detects_forbidden_field_at_any_depth() -> None:
    assert _forbidden_in(_NestedTechnicianOut) == {"unit_price"}
    assert "unit_price" in _forbidden_in(_OrderTechnicianOut)


def test_scanner_passes_a_clean_schema() -> None:
    assert _forbidden_in(_CleanTechnicianOut) == set()


# E03-02, criterio 7: el técnico ve el nombre del contacto del lugar, nunca su teléfono ni
# su email (le permitirían contactar al cliente por fuera de la empresa).
class _SiteWithPhoneTechnicianOut(BaseModel):
    address: str
    phone: str
    email: str


def test_scanner_detects_contact_phone_and_email() -> None:
    assert _forbidden_in(_SiteWithPhoneTechnicianOut) == {"phone", "email"}
