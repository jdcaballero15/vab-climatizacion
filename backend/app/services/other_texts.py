"""Textos de "Otro" para sumar a los catálogos (E02-07).

Lo que las escuadrillas escriben a mano en falla, reparación o material se agrupa por
texto normalizado (sin mayúsculas ni espacios de más) con sus repeticiones. Administración
lo promueve a la lista (nuevo o a un valor que ya existe) y las órdenes anteriores pasan a
referenciarlo; o lo descarta, y deja de mostrarse sin tocar las órdenes.
"""

import uuid
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.api.schemas.catalog import FailureCreate, RepairCreate
from app.api.schemas.part import PartCreate
from app.db.models.catalog import Failure, Repair
from app.db.models.other_text import DismissedOtherText
from app.db.models.part import Part, PartUsage
from app.db.models.user import User
from app.db.models.work_order import WorkOrderClosure
from app.services import catalog as catalog_service
from app.services import parts as parts_service

Kind = Literal["failure", "repair", "part"]


@dataclass(frozen=True)
class OtherText:
    text_key: str
    # La forma más usada, para mostrar y como nombre propuesto.
    text: str
    count: int


class TargetNotFoundError(Exception):
    pass


def text_key(value: str | None) -> str:
    return " ".join((value or "").split()).lower()


def _column(kind: Kind) -> InstrumentedAttribute[str | None]:
    if kind == "failure":
        return WorkOrderClosure.failure_other_text
    if kind == "repair":
        return WorkOrderClosure.repair_other_text
    return PartUsage.other_text


async def list_texts(session: AsyncSession, kind: Kind) -> list[OtherText]:
    """Los textos con sus repeticiones, el más repetido primero, sin los descartados."""
    column = _column(kind)
    model = PartUsage if kind == "part" else WorkOrderClosure
    rows = (
        await session.execute(
            select(column, func.count())
            .where(column.is_not(None), model.deleted_at.is_(None))
            .group_by(column)
        )
    ).all()
    dismissed = set(
        (
            await session.scalars(
                select(DismissedOtherText.text_key).where(
                    DismissedOtherText.kind == kind, DismissedOtherText.deleted_at.is_(None)
                )
            )
        ).all()
    )
    totals: Counter[str] = Counter()
    forms: dict[str, Counter[str]] = {}
    for value, count in rows:
        key = text_key(value)
        if not key or key in dismissed:
            continue
        totals[key] += count
        forms.setdefault(key, Counter())[" ".join((value or "").split())] += count
    return [
        OtherText(text_key=key, text=_display(forms[key]), count=count)
        for key, count in sorted(totals.items(), key=lambda item: (-item[1], item[0]))
    ]


def _display(forms: Counter[str]) -> str:
    """La forma más usada; en un empate, la que está escrita como oración."""

    def rank(form: str) -> tuple[int, int, str]:
        sentence = form[:1].isupper() and not form.isupper()
        return (-forms[form], 0 if sentence else 1, form)

    return min(forms, key=rank)


async def promote(
    session: AsyncSession,
    kind: Kind,
    key: str,
    *,
    name: str | None,
    target_id: uuid.UUID | None,
    failure_id: uuid.UUID | None,
    equipment_type_id: uuid.UUID | None,
    unit: str | None,
    actor: User,
) -> int:
    """Crea el valor (o usa uno existente) y pasa a referenciarlo cada orden con ese
    texto. Devuelve cuántas se actualizaron."""
    if target_id is not None:
        await check_target(session, kind, target_id)
    target = target_id or await _create(
        session, kind, name or key, failure_id, equipment_type_id, unit, actor
    )
    matches = await _matching_ids(session, kind, key)
    if kind == "part":
        await session.execute(
            update(PartUsage)
            .where(PartUsage.id.in_(matches))
            .values(part_id=target, other_text=None)
        )
    elif kind == "failure":
        await session.execute(
            update(WorkOrderClosure)
            .where(WorkOrderClosure.id.in_(matches))
            .values(failure_id=target, failure_other_text=None)
        )
    else:
        await session.execute(
            update(WorkOrderClosure)
            .where(WorkOrderClosure.id.in_(matches))
            .values(repair_id=target, repair_other_text=None)
        )
    await session.commit()
    return len(matches)


async def dismiss(session: AsyncSession, kind: Kind, key: str) -> None:
    session.add(DismissedOtherText(kind=kind, text_key=text_key(key)))
    await session.commit()


async def _matching_ids(session: AsyncSession, kind: Kind, key: str) -> Sequence[uuid.UUID]:
    column = _column(kind)
    model = PartUsage if kind == "part" else WorkOrderClosure
    rows = (
        await session.execute(
            select(model.id, column).where(column.is_not(None), model.deleted_at.is_(None))
        )
    ).all()
    return [row_id for row_id, value in rows if text_key(value) == text_key(key)]


async def _create(
    session: AsyncSession,
    kind: Kind,
    name: str,
    failure_id: uuid.UUID | None,
    equipment_type_id: uuid.UUID | None,
    unit: str | None,
    actor: User,
) -> uuid.UUID:
    if kind == "failure":
        failure = await catalog_service.create_failure(
            session, FailureCreate(name=name, equipment_type_id=equipment_type_id)
        )
        return failure.id
    if kind == "repair":
        if failure_id is None or await session.get(Failure, failure_id) is None:
            raise TargetNotFoundError
        repair = await catalog_service.create_repair(
            session,
            RepairCreate(name=name, failure_id=failure_id, equipment_type_id=equipment_type_id),
        )
        return repair.id
    part = await parts_service.create_part(
        session, PartCreate(name=name, unit=unit or "unidad"), actor
    )
    return part.id


async def check_target(session: AsyncSession, kind: Kind, target_id: uuid.UUID) -> None:
    model: type[Failure] | type[Repair] | type[Part] = (
        Failure if kind == "failure" else Repair if kind == "repair" else Part
    )
    if await session.get(model, target_id) is None:
        raise TargetNotFoundError
