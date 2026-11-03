"""Búsqueda de clientes y equipos para la oficina (E03-06).

Cada palabra de la búsqueda tiene que estar en algún dato del cliente o del equipo, sin
mayúsculas ni acentos. Si no, alcanza con que se parezca (pg_trgm): tolera errores de
tipeo, salvo con números. Primero van las que contienen todas las palabras, después las
más parecidas.
"""

import re
from collections.abc import Sequence

from sqlalchemy import ColumnElement, Row, and_, case, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.db.models.catalog import EquipmentType
from app.db.models.client import Client, ClientContact, ClientSite
from app.db.models.equipment import Equipment

_ACCENTED = "áàäâéèëêíìïîóòöôúùüûñç"
_PLAIN = "aaaaeeeeiiiioooouuuunc"
# Desde cuánto parecido una búsqueda con errores cuenta, y desde qué largo se intenta.
_SIMILARITY = 0.5
_MIN_FUZZY_LENGTH = 4
_MIN_DIGITS = 3

# Cliente: el cliente, la dirección de su primer domicilio y si contiene todas las palabras.
type ClientHit = Row[Client, str | None]
# Equipo: el equipo, su tipo, cliente (id y nombre) y domicilio (rótulo y dirección).
type EquipmentHit = Row[Equipment, str, Client, str | None, str]


def _plain(value: ColumnElement[str] | InstrumentedAttribute[str]) -> ColumnElement[str]:
    return func.translate(func.lower(value), _ACCENTED, _PLAIN)


def _like(text: str) -> str:
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _matches(haystack: ColumnElement[str], query: str) -> tuple[ColumnElement[bool], ...]:
    """Contiene todas las palabras y, aparte, se parece. La búsqueda ya viene normalizada."""
    words = []
    for word in query.split():
        options = [haystack.like(_like(word), escape="\\")]
        digits = re.sub(r"\D", "", word)
        # "421-5566" encuentra el teléfono guardado como "(0385) 421 5566". Solo si no tiene
        # letras: "ea1064" es un código y no tiene que traer "EF1064301".
        if len(digits) >= _MIN_DIGITS and digits != word and not re.search(r"[a-z]", word):
            options.append(haystack.like(_like(digits), escape="\\"))
        words.append(or_(*options))
    contains = and_(*words)
    # Con números (códigos, teléfonos) el parecido trae vecinos: "10643" no es "10642".
    fuzzy = len(query) >= _MIN_FUZZY_LENGTH and not re.search(r"\d", query)
    similar = func.word_similarity(query, haystack) >= _SIMILARITY if fuzzy else literal(False)
    return contains, similar


class SearchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def clients(
        self, query: str, *, include_deleted: bool, limit: int
    ) -> Sequence[ClientHit]:
        addresses = (
            select(func.string_agg(func.concat_ws(" ", ClientSite.label, ClientSite.address), " "))
            .where(ClientSite.client_id == Client.id, ClientSite.deleted_at.is_(None))
            .scalar_subquery()
        )
        # Los teléfonos, solo con los números: se escriben con o sin espacios y guiones.
        phones = (
            select(func.string_agg(func.regexp_replace(ClientContact.phone, r"\D", "", "g"), " "))
            .where(ClientContact.client_id == Client.id, ClientContact.deleted_at.is_(None))
            .scalar_subquery()
        )
        haystack = func.concat_ws(
            " ", _plain(func.concat_ws(" ", Client.name, Client.number, addresses)), phones
        )
        contains, similar = _matches(haystack, query)
        first_address = (
            select(ClientSite.address)
            .where(ClientSite.client_id == Client.id, ClientSite.deleted_at.is_(None))
            .order_by(ClientSite.created_at, ClientSite.id)
            .limit(1)
            .scalar_subquery()
        )
        stmt = (
            select(Client, first_address)
            .where(or_(contains, similar))
            .order_by(
                case((contains, 0), else_=1),
                func.word_similarity(query, _plain(Client.name)).desc(),
                Client.name,
            )
            .limit(limit)
        )
        if not include_deleted:
            stmt = stmt.where(Client.deleted_at.is_(None))
        return (await self.session.execute(stmt)).all()

    async def equipment(
        self, query: str, *, include_deleted: bool, limit: int
    ) -> Sequence[EquipmentHit]:
        haystack = _plain(
            func.concat_ws(
                " ",
                Equipment.internal_code,
                Equipment.serial_number,
                Equipment.brand,
                Equipment.model,
                Equipment.location_note,
                EquipmentType.name,
            )
        )
        contains, similar = _matches(haystack, query)
        stmt = (
            select(Equipment, EquipmentType.name, Client, ClientSite.label, ClientSite.address)
            .join(EquipmentType, EquipmentType.id == Equipment.equipment_type_id)
            .join(ClientSite, ClientSite.id == Equipment.client_site_id)
            .join(Client, Client.id == ClientSite.client_id)
            .where(or_(contains, similar))
            .order_by(
                case((contains, 0), else_=1),
                func.word_similarity(query, haystack).desc(),
                Equipment.internal_code,
            )
            .limit(limit)
        )
        if not include_deleted:
            stmt = stmt.where(Equipment.deleted_at.is_(None))
        return (await self.session.execute(stmt)).all()
