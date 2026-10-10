"""public worlds: featured flag, play stats and anonymous creator

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("worlds") as batch:
        batch.add_column(
            sa.Column("featured", sa.Boolean, nullable=False, server_default=sa.false())
        )
        batch.add_column(
            sa.Column("play_count", sa.Integer, nullable=False, server_default="0")
        )
        batch.add_column(
            sa.Column("last_played_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch.add_column(sa.Column("creator_hash", sa.String(64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("worlds") as batch:
        batch.drop_column("creator_hash")
        batch.drop_column("last_played_at")
        batch.drop_column("play_count")
        batch.drop_column("featured")
