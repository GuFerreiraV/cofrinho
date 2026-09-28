"""estado do FSM no banco e criado_em com fuso horário

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("despesas") as batch:
        batch.alter_column(
            "criado_em",
            type_=sa.DateTime(timezone=True),
            existing_type=sa.DateTime(),
            existing_nullable=False,
        )
    op.create_table(
        "fsm_estados",
        sa.Column("chave", sa.String(255), primary_key=True),
        sa.Column("estado", sa.String(255), nullable=True),
        sa.Column("dados", sa.JSON(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("fsm_estados")
    with op.batch_alter_table("despesas") as batch:
        batch.alter_column(
            "criado_em",
            type_=sa.DateTime(),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=False,
        )
