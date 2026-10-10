"""Generation attempts and private timing metrics."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("worlds") as batch:
        batch.add_column(
            sa.Column(
                "generation_attempt", sa.Integer, nullable=False, server_default="1"
            )
        )
    with op.batch_alter_table("world_events") as batch:
        batch.add_column(
            sa.Column("attempt", sa.Integer, nullable=False, server_default="1")
        )
        batch.add_column(
            sa.Column("elapsed_seconds", sa.Float, nullable=False, server_default="0")
        )
        batch.add_column(sa.Column("metrics", sa.Text, nullable=True))
        batch.create_index("ix_world_events_attempt", ["world_id", "attempt", "id"])


def downgrade() -> None:
    with op.batch_alter_table("world_events") as batch:
        batch.drop_index("ix_world_events_attempt")
        batch.drop_column("metrics")
        batch.drop_column("elapsed_seconds")
        batch.drop_column("attempt")
    with op.batch_alter_table("worlds") as batch:
        batch.drop_column("generation_attempt")
