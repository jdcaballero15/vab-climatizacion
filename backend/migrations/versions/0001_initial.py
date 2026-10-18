"""Linea base del esquema.

No crea tablas de dominio todavia: establece el control de versiones de Alembic
para que las historias siguientes agreguen tablas de forma reversible.

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-17

"""

from collections.abc import Sequence

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
