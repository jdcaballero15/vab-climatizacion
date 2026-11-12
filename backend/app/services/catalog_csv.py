"""Importar y exportar catálogos por CSV (E02-08).

La exportación tiene las mismas columnas que acepta la importación. La importación primero
se previsualiza: altas, cambios y errores con su fila. Con algún error no se aplica nada;
sin errores, todo se aplica en una sola transacción. Se compara por nombre, sin mayúsculas
ni espacios de más (y, en fallas y reparaciones, por su tipo de equipo y su falla).
"""

import csv
import io
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.catalog import EquipmentType, Failure, Repair, WorkType
from app.db.models.part import Part

Catalog = Literal["work-types", "equipment-types", "failures", "repairs", "parts"]
COLUMNS: dict[str, tuple[str, ...]] = {
    "work-types": ("nombre", "activo"),
    "equipment-types": ("nombre", "prefijo", "activo"),
    "failures": ("nombre", "tipo_de_equipo", "activo"),
    "repairs": ("nombre", "falla", "tipo_de_equipo", "activo"),
    "parts": ("nombre", "unidad", "codigo", "activo"),
}
_YES = {"si", "sí", "s", "1", "true", "verdadero", "x", ""}
_NO = {"no", "n", "0", "false", "falso"}
_MAX = 255


@dataclass
class RowChange:
    row: int
    name: str
    # Qué cambia: "activo: sí → no".
    detail: str = ""


@dataclass
class Preview:
    creates: list[RowChange] = field(default_factory=list)
    changes: list[RowChange] = field(default_factory=list)
    errors: list[RowChange] = field(default_factory=list)
    unchanged: int = 0
    # Lo que se aplica: funciones que crean o cambian, en orden.
    _actions: list[Callable[[AsyncSession], None]] = field(default_factory=list, repr=False)


class CsvFormatError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _key(value: str | None) -> str:
    return " ".join((value or "").split()).lower()


def _yes(value: str) -> bool | None:
    clean = value.strip().lower()
    if clean in _YES:
        return True
    if clean in _NO:
        return False
    return None


def _flag(value: bool) -> str:
    return "sí" if value else "no"


async def export_csv(session: AsyncSession, catalog: Catalog) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(COLUMNS[catalog])
    types = {t.id: t.name for t in (await session.scalars(select(EquipmentType))).all()}
    if catalog == "work-types":
        for item in await _all(session, WorkType):
            writer.writerow([item.name, _flag(item.is_active)])
    elif catalog == "equipment-types":
        for et in await _all(session, EquipmentType):
            writer.writerow([et.name, et.code_prefix or "", _flag(et.is_active)])
    elif catalog == "failures":
        for failure in await _all(session, Failure):
            type_name = (
                types.get(failure.equipment_type_id, "") if failure.equipment_type_id else ""
            )
            writer.writerow([failure.name, type_name, _flag(failure.is_active)])
    elif catalog == "repairs":
        failures = {f.id: f.name for f in await _all(session, Failure)}
        for repair in await _all(session, Repair):
            type_name = types.get(repair.equipment_type_id, "") if repair.equipment_type_id else ""
            writer.writerow(
                [
                    repair.name,
                    failures.get(repair.failure_id, ""),
                    type_name,
                    _flag(repair.is_active),
                ]
            )
    else:
        for part in await _all(session, Part):
            writer.writerow([part.name, part.unit, part.code or "", _flag(part.is_active)])
    return buffer.getvalue()


def _type(types: dict[Any, str], item: Failure | Repair) -> str:
    return types.get(item.equipment_type_id, "") if item.equipment_type_id else ""


async def _all(session: AsyncSession, model: type[Any]) -> list[Any]:
    return list(
        (
            await session.scalars(
                select(model).where(model.deleted_at.is_(None)).order_by(model.name)
            )
        ).all()
    )


def _rows(content: str, catalog: Catalog) -> list[tuple[int, dict[str, str]]]:
    reader = csv.DictReader(io.StringIO(content.lstrip("﻿")))
    header = [h.strip().lower() for h in reader.fieldnames or []]
    missing = [c for c in COLUMNS[catalog] if c not in header]
    if missing:
        raise CsvFormatError(f"Faltan las columnas: {', '.join(missing)}.")
    reader.fieldnames = header
    return [
        (number, {k: (v or "").strip() for k, v in row.items() if k})
        for number, row in enumerate(reader, start=2)
        if any((v or "").strip() for v in row.values() if isinstance(v, str))
    ]


async def preview(session: AsyncSession, catalog: Catalog, content: str) -> Preview:
    result = Preview()
    rows = _rows(content, catalog)
    types = {_key(t.name): t for t in await _all(session, EquipmentType)}
    seen: set[tuple[str, ...]] = set()
    if catalog in ("work-types", "equipment-types", "parts"):
        model = {"work-types": WorkType, "equipment-types": EquipmentType, "parts": Part}[catalog]
        existing = {_key(item.name): item for item in await _all(session, model)}
        for number, row in rows:
            name, active = row.get("nombre", ""), _yes(row.get("activo", ""))
            problem = _basic_problem(name, active)
            if not problem and (_key(name),) in seen:
                problem = "repetido en el archivo"
            if problem:
                result.errors.append(RowChange(number, name, problem))
                continue
            seen.add((_key(name),))
            values: dict[str, object] = {"is_active": bool(active)}
            if catalog == "equipment-types":
                values["code_prefix"] = row.get("prefijo", "").upper() or None
            if catalog == "parts":
                values["unit"] = row.get("unidad", "") or "unidad"
                values["code"] = row.get("codigo", "") or None
            _plan(result, number, name, existing.get(_key(name)), model, values)
        return result

    failures: dict[str, Failure] = {}
    if catalog == "repairs":
        for failure in await _all(session, Failure):
            failures.setdefault(_key(failure.name), failure)
    model = Failure if catalog == "failures" else Repair
    existing_scoped = {_scope_key(item): item for item in await _all(session, model)}
    for number, row in rows:
        name, active = row.get("nombre", ""), _yes(row.get("activo", ""))
        problem = _basic_problem(name, active)
        type_name = row.get("tipo_de_equipo", "")
        equipment_type = types.get(_key(type_name)) if type_name else None
        if not problem and type_name and equipment_type is None:
            problem = f"no existe el tipo de equipo «{type_name}»"
        failure = None
        if not problem and catalog == "repairs":
            failure = failures.get(_key(row.get("falla", "")))
            if failure is None:
                problem = f"no existe la falla «{row.get('falla', '')}»"
        scope = (
            _key(name),
            str(equipment_type.id) if equipment_type else "",
            str(failure.id) if failure else "",
        )
        if not problem and scope in seen:
            problem = "repetido en el archivo"
        if problem:
            result.errors.append(RowChange(number, name, problem))
            continue
        seen.add(scope)
        values = {
            "is_active": bool(active),
            "equipment_type_id": equipment_type.id if equipment_type else None,
        }
        if failure is not None:
            values["failure_id"] = failure.id
        _plan(result, number, name, existing_scoped.get(scope), model, values)
    return result


def _scope_key(item: Failure | Repair) -> tuple[str, ...]:
    return (
        _key(item.name),
        str(item.equipment_type_id or ""),
        str(item.failure_id) if isinstance(item, Repair) else "",
    )


def _basic_problem(name: str, active: bool | None) -> str | None:
    if not name.strip():
        return "falta el nombre"
    if len(name) > _MAX:
        return f"el nombre tiene más de {_MAX} caracteres"
    if active is None:
        return "activo tiene que ser sí o no"
    return None


def _plan(
    result: Preview,
    number: int,
    name: str,
    current: object | None,
    model: type,
    values: dict[str, object],
) -> None:
    clean = " ".join(name.split())
    if current is None:
        result.creates.append(RowChange(number, clean))
        result._actions.append(lambda session: session.add(model(name=clean, **values)))
        return
    diffs = [
        f"{attr}: {_shown(getattr(current, attr))} → {_shown(value)}"
        for attr, value in values.items()
        if getattr(current, attr) != value
    ]
    if not diffs:
        result.unchanged += 1
        return
    result.changes.append(RowChange(number, clean, "; ".join(diffs)))

    def change(_: AsyncSession, target: object = current) -> None:
        for attr, value in values.items():
            setattr(target, attr, value)

    result._actions.append(change)


def _shown(value: object) -> str:
    if isinstance(value, bool):
        return _flag(value)
    return "-" if value is None else str(value)


async def apply(session: AsyncSession, catalog: Catalog, content: str) -> Preview:
    """Aplica todo en una transacción; con errores no aplica nada (criterio 2)."""
    result = await preview(session, catalog, content)
    if result.errors:
        return result
    for action in result._actions:
        action(session)
    await session.commit()
    return result
