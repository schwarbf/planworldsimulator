"""The model a world is generated with."""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("worlds") as batch:
        batch.add_column(sa.Column("generation_model", sa.String(64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("worlds") as batch:
        batch.drop_column("generation_model")
