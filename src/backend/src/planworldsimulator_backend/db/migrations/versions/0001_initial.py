"""initial schema

Revision ID: 0001
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "worlds",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("seed", sa.Integer, nullable=False),
        sa.Column("difficulty", sa.Integer, nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("storyline", sa.Text, nullable=True),
        sa.Column("path", sa.String(500), nullable=True),
        sa.Column("running", sa.Boolean, nullable=False),
        sa.Column("port", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "world_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "world_id", sa.String(32), sa.ForeignKey("worlds.id"), nullable=False
        ),
        sa.Column("step", sa.String(32), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_world_events_world_id", "world_events", ["world_id"])


def downgrade() -> None:
    op.drop_index("ix_world_events_world_id", table_name="world_events")
    op.drop_table("world_events")
    op.drop_table("worlds")
