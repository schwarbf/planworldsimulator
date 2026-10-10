"""drop worlds.difficulty: every world now ships with all difficulty levels

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("worlds") as batch:
        batch.drop_column("difficulty")


def downgrade() -> None:
    with op.batch_alter_table("worlds") as batch:
        batch.add_column(
            sa.Column("difficulty", sa.Integer, nullable=False, server_default="2")
        )
