"""auditoría de cambios sin clave foránea al usuario (E12-01)

Revision ID: b2d4f6a8c013
Revises: a1c3e5f7b902
Create Date: 2026-11-10

audit_event pasa a registrar los cambios de toda la app: el usuario queda como dato, sin
depender de la tabla de usuarios, y se indexa para filtrar por él.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "b2d4f6a8c013"
down_revision: str | None = "a1c3e5f7b902"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("audit_event_actor_id_fkey", "audit_event", type_="foreignkey")
    op.create_index(op.f("ix_audit_event_actor_id"), "audit_event", ["actor_id"])
    op.create_index("ix_audit_event_occurred_at", "audit_event", ["occurred_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_event_occurred_at", table_name="audit_event")
    op.drop_index(op.f("ix_audit_event_actor_id"), table_name="audit_event")
    op.create_foreign_key(
        "audit_event_actor_id_fkey", "audit_event", "app_user", ["actor_id"], ["id"]
    )
