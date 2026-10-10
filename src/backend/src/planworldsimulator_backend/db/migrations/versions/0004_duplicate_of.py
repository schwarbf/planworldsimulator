"""worlds.duplicate_of: the world that already has the requested name

Revision ID: 0004
Revises: 0003
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("worlds") as batch:
        batch.add_column(sa.Column("duplicate_of", sa.String(32), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("worlds") as batch:
        batch.drop_column("duplicate_of")
