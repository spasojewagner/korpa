"""Compact monthly history: per-format detail for recent months, one row per product after that."""

import sqlalchemy as sa
from alembic import op

revision = "5c1e9a7d3b20"
down_revision = "430d4ce8c2a1"
branch_labels = None
depends_on = None

# Compacted months plus live per-format months aggregated on read. A late per-format row for a
# month that is already compacted is left out here until the next compaction merges it.
VIEW = """
CREATE VIEW monthly_price_history AS
SELECT barcode, month, min_regular, median_regular, max_regular, min_discounted, n_formats
FROM monthly_prices
UNION ALL
SELECT s.barcode, s.month, min(s.regular),
       percentile_disc(0.5) WITHIN GROUP (ORDER BY s.regular),
       max(s.regular), min(s.discounted), count(*)::smallint
FROM monthly_snapshots s
WHERE NOT EXISTS (
    SELECT 1 FROM monthly_prices p WHERE p.barcode = s.barcode AND p.month = s.month
)
GROUP BY s.barcode, s.month
"""


def upgrade() -> None:
    op.create_table(
        "monthly_prices",
        sa.Column("barcode", sa.CHAR(13), sa.ForeignKey("products.barcode"), primary_key=True),
        sa.Column("month", sa.Date, primary_key=True),
        sa.Column("min_regular", sa.Integer, nullable=False),
        sa.Column("median_regular", sa.Integer, nullable=False),
        sa.Column("max_regular", sa.Integer, nullable=False),
        sa.Column("min_discounted", sa.Integer),
        sa.Column("n_formats", sa.SmallInteger, nullable=False),
    )
    op.create_index(
        "ix_monthly_snapshots_barcode_month", "monthly_snapshots", ["barcode", "month"]
    )
    op.execute(VIEW)


def downgrade() -> None:
    op.execute("DROP VIEW monthly_price_history")
    op.drop_index("ix_monthly_snapshots_barcode_month", table_name="monthly_snapshots")
    op.drop_table("monthly_prices")
