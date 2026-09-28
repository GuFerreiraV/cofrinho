"""criar tabela despesas

Revision ID: 0001
Revises:
Create Date: 2026-09-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "despesas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("valor", sa.Numeric(10, 2), nullable=False),
        sa.Column("forma_pagamento", sa.String(), nullable=False),
        sa.Column("data", sa.Date(), nullable=False),
        sa.Column("descricao", sa.String(), nullable=False),
        sa.Column("categoria", sa.String(), nullable=False),
        sa.Column("criado_em", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_despesas_user_id", "despesas", ["user_id"])
    op.create_index("ix_despesas_forma_pagamento", "despesas", ["forma_pagamento"])
    op.create_index("ix_despesas_data", "despesas", ["data"])
    op.create_index("ix_despesas_categoria", "despesas", ["categoria"])


def downgrade() -> None:
    op.drop_index("ix_despesas_categoria", table_name="despesas")
    op.drop_index("ix_despesas_data", table_name="despesas")
    op.drop_index("ix_despesas_forma_pagamento", table_name="despesas")
    op.drop_index("ix_despesas_user_id", table_name="despesas")
    op.drop_table("despesas")
