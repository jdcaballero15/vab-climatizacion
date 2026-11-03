"""extensión pg_trgm para buscar con errores de tipeo (E03-06)

Revision ID: 22c25d75ac2c
Revises: 33e9362dae73
Create Date: 2026-11-03

word_similarity para que "farmasia" encuentre "Farmacia". pg_trgm es una extensión de
confianza: la crea el dueño de la base, sin superusuario (también en Render).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "22c25d75ac2c"
down_revision: str | None = "33e9362dae73"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")


def downgrade() -> None:
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
