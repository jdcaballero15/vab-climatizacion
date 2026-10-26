"""crear work_type y task con los tipos de trabajo iniciales

Revision ID: 51d29e6b730e
Revises: 65ecfee80f82
Create Date: 2026-10-26

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "51d29e6b730e"
down_revision: str | None = "65ecfee80f82"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Los seis tipos del relevamiento. Van en la migración y no en make seed porque
# también tienen que existir en producción (E02-01, criterio 9). Siguen editables.
INITIAL_WORK_TYPES = (
    "Instalación",
    "Reparación",
    "Service",
    "Devolución",
    "Retiro",
    "Relevamiento",
)


def _timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    work_type = op.create_table(
        "work_type",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_work_type_name", "work_type", [sa.text("lower(name)")], unique=True)

    op.create_table(
        "task",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("work_type_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["work_type_id"], ["work_type.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_task_work_type_id"), "task", ["work_type_id"], unique=False)
    op.create_index(
        "uq_task_work_type_name", "task", ["work_type_id", sa.text("lower(name)")], unique=True
    )

    op.bulk_insert(
        work_type,
        [{"id": uuid.uuid4(), "name": name, "is_active": True} for name in INITIAL_WORK_TYPES],
    )


def downgrade() -> None:
    op.drop_index("uq_task_work_type_name", table_name="task")
    op.drop_index(op.f("ix_task_work_type_id"), table_name="task")
    op.drop_table("task")
    op.drop_index("uq_work_type_name", table_name="work_type")
    op.drop_table("work_type")
