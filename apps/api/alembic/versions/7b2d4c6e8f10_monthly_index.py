"""Allow unpublished index values, exclusion counts and overall code zero."""

import sqlalchemy as sa
from alembic import op

revision = "7b2d4c6e8f10"
down_revision = "5c1e9a7d3b20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_prices_current_barcode", table_name="prices_current")
    op.create_index(
        "ix_prices_current_index_median",
        "prices_current",
        ["barcode", "regular"],
        postgresql_include=["list_date"],
    )
    op.drop_constraint("index_monthly_category_code_fkey", "index_monthly", type_="foreignkey")
    op.alter_column("index_monthly", "value", existing_type=sa.Numeric(12, 4), nullable=True)
    op.add_column(
        "index_monthly", sa.Column("n_excluded", sa.Integer(), nullable=False, server_default="0")
    )
    op.create_check_constraint(
        "ck_index_category", "index_monthly", "category_code BETWEEN 0 AND 25"
    )


def downgrade() -> None:
    op.create_index("ix_prices_current_barcode", "prices_current", ["barcode"])
    op.drop_index("ix_prices_current_index_median", table_name="prices_current")
    op.execute("DELETE FROM index_monthly WHERE category_code = 0 OR value IS NULL")
    op.drop_constraint("ck_index_category", "index_monthly", type_="check")
    op.drop_column("index_monthly", "n_excluded")
    op.alter_column("index_monthly", "value", existing_type=sa.Numeric(12, 4), nullable=False)
    op.create_foreign_key(
        "index_monthly_category_code_fkey",
        "index_monthly",
        "categories",
        ["category_code"],
        ["code"],
    )
