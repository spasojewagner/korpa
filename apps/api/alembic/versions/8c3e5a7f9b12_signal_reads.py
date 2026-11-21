"""Cover effective-price reads for unusual-change signals."""

from alembic import op

revision = "8c3e5a7f9b12"
down_revision = "7b2d4c6e8f10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_prices_current_index_median", table_name="prices_current")
    op.create_index(
        "ix_prices_current_index_median",
        "prices_current",
        ["barcode", "regular"],
        postgresql_include=["list_date", "discounted", "disc_from", "disc_to"],
    )


def downgrade() -> None:
    op.drop_index("ix_prices_current_index_median", table_name="prices_current")
    op.create_index(
        "ix_prices_current_index_median",
        "prices_current",
        ["barcode", "regular"],
        postgresql_include=["list_date"],
    )
