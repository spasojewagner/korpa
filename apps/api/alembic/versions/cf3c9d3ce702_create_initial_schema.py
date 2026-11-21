"""create initial schema"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "cf3c9d3ce702"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_table(
        "categories",
        sa.Column("code", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.CheckConstraint("code BETWEEN 1 AND 25"),
        sa.PrimaryKeyConstraint("code"),
    )
    op.create_table(
        "retailers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("dataset_id", sa.Text(), nullable=False),
        sa.Column("resource_url", sa.Text(), nullable=False),
        sa.Column("last_etag", sa.Text(), nullable=True),
        sa.Column("last_modified", sa.Text(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_table(
        "index_monthly",
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("category_code", sa.Integer(), nullable=False),
        sa.Column("value", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("n_products", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["category_code"],
            ["categories.code"],
        ),
        sa.PrimaryKeyConstraint("month", "category_code"),
    )
    op.create_table(
        "ingest_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("retailer_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("rows_total", sa.Integer(), nullable=False),
        sa.Column("rows_valid", sa.Integer(), nullable=False),
        sa.Column("errors_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["retailer_id"],
            ["retailers.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "products",
        sa.Column("barcode", sa.CHAR(length=13), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("brand", sa.Text(), nullable=False),
        sa.Column("unit", sa.Text(), nullable=False),
        sa.Column("category_code", sa.Integer(), nullable=False),
        sa.Column("search_tsv", postgresql.TSVECTOR(), nullable=True),
        sa.CheckConstraint("barcode ~ '^[0-9]{13}$'"),
        sa.ForeignKeyConstraint(
            ["category_code"],
            ["categories.code"],
        ),
        sa.PrimaryKeyConstraint("barcode"),
    )
    op.create_index(
        "ix_products_name_trgm",
        "products",
        ["name"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_products_search", "products", ["search_tsv"], unique=False, postgresql_using="gin"
    )
    op.create_table(
        "retail_formats",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("retailer_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["retailer_id"],
            ["retailers.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("retailer_id", "name"),
    )
    op.create_table(
        "monthly_snapshots",
        sa.Column("format_id", sa.Integer(), nullable=False),
        sa.Column("barcode", sa.CHAR(length=13), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("regular", sa.Integer(), nullable=False),
        sa.Column("discounted", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["barcode"],
            ["products.barcode"],
        ),
        sa.ForeignKeyConstraint(
            ["format_id"],
            ["retail_formats.id"],
        ),
        sa.PrimaryKeyConstraint("format_id", "barcode", "month"),
    )
    op.create_table(
        "price_changes",
        sa.Column("format_id", sa.Integer(), nullable=False),
        sa.Column("barcode", sa.CHAR(length=13), nullable=False),
        sa.Column("changed_on", sa.Date(), nullable=False),
        sa.Column("regular", sa.Integer(), nullable=False),
        sa.Column("discounted", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["barcode"],
            ["products.barcode"],
        ),
        sa.ForeignKeyConstraint(
            ["format_id"],
            ["retail_formats.id"],
        ),
        sa.PrimaryKeyConstraint("format_id", "barcode", "changed_on"),
    )
    op.create_index("ix_price_changes_date", "price_changes", ["changed_on"], unique=False)
    op.create_table(
        "prices_current",
        sa.Column("format_id", sa.Integer(), nullable=False),
        sa.Column("barcode", sa.CHAR(length=13), nullable=False),
        sa.Column("regular", sa.Integer(), nullable=False),
        sa.Column("discounted", sa.Integer(), nullable=True),
        sa.Column("disc_from", sa.Date(), nullable=True),
        sa.Column("disc_to", sa.Date(), nullable=True),
        sa.Column("unit_price", sa.Integer(), nullable=False),
        sa.Column("vat", sa.Integer(), nullable=False),
        sa.Column("list_date", sa.Date(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("discounted IS NULL OR discounted BETWEEN 0 AND regular"),
        sa.CheckConstraint("regular >= 0 AND unit_price >= 0"),
        sa.ForeignKeyConstraint(
            ["barcode"],
            ["products.barcode"],
        ),
        sa.ForeignKeyConstraint(
            ["format_id"],
            ["retail_formats.id"],
        ),
        sa.PrimaryKeyConstraint("format_id", "barcode"),
    )
    op.create_table(
        "product_names",
        sa.Column("barcode", sa.CHAR(length=13), nullable=False),
        sa.Column("retailer_id", sa.Integer(), nullable=False),
        sa.Column("raw_name", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["barcode"],
            ["products.barcode"],
        ),
        sa.ForeignKeyConstraint(
            ["retailer_id"],
            ["retailers.id"],
        ),
        sa.PrimaryKeyConstraint("barcode", "retailer_id"),
    )


def downgrade() -> None:
    op.drop_table("product_names")
    op.drop_table("prices_current")
    op.drop_index("ix_price_changes_date", table_name="price_changes")
    op.drop_table("price_changes")
    op.drop_table("monthly_snapshots")
    op.drop_table("retail_formats")
    op.drop_index("ix_products_search", table_name="products", postgresql_using="gin")
    op.drop_index(
        "ix_products_name_trgm",
        table_name="products",
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )
    op.drop_table("products")
    op.drop_table("ingest_runs")
    op.drop_table("index_monthly")
    op.drop_table("retailers")
    op.drop_table("categories")
