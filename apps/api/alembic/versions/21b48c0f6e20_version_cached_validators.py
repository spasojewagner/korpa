"""Bind cached resource validators to the parsing profile."""

import sqlalchemy as sa
from alembic import op

revision = "21b48c0f6e20"
down_revision = "cf3c9d3ce702"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("retailers", sa.Column("validator_profile", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("retailers", "validator_profile")
