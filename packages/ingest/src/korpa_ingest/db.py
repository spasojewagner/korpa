"""Shared database schema. All schema changes are applied through Alembic."""

import os

import sqlalchemy as sa
from dotenv import load_dotenv
from sqlalchemy.dialects.postgresql import TSVECTOR

metadata = sa.MetaData()

retailers = sa.Table(
    "retailers",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("name", sa.Text, nullable=False),
    sa.Column("slug", sa.Text, nullable=False, unique=True),
    sa.Column("dataset_id", sa.Text, nullable=False),
    sa.Column("resource_url", sa.Text, nullable=False),
    sa.Column("last_etag", sa.Text),
    sa.Column("last_modified", sa.Text),
    sa.Column("last_seen_at", sa.DateTime(timezone=True)),
)
retail_formats = sa.Table(
    "retail_formats",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("retailer_id", sa.ForeignKey("retailers.id"), nullable=False),
    sa.Column("name", sa.Text, nullable=False),
    sa.UniqueConstraint("retailer_id", "name"),
)
categories = sa.Table(
    "categories",
    metadata,
    sa.Column("code", sa.Integer, primary_key=True),
    sa.Column("name", sa.Text, nullable=False),
    sa.CheckConstraint("code BETWEEN 1 AND 25"),
)
products = sa.Table(
    "products",
    metadata,
    sa.Column("barcode", sa.CHAR(13), primary_key=True),
    sa.Column("name", sa.Text, nullable=False),
    sa.Column("brand", sa.Text, nullable=False),
    sa.Column("unit", sa.Text, nullable=False),
    sa.Column("category_code", sa.ForeignKey("categories.code"), nullable=False),
    sa.Column("search_tsv", TSVECTOR),
    sa.CheckConstraint("barcode ~ '^[0-9]{13}$'"),
)
sa.Index(
    "ix_products_name_trgm",
    products.c.name,
    postgresql_using="gin",
    postgresql_ops={"name": "gin_trgm_ops"},
)
sa.Index("ix_products_search", products.c.search_tsv, postgresql_using="gin")
product_names = sa.Table(
    "product_names",
    metadata,
    sa.Column("barcode", sa.ForeignKey("products.barcode"), primary_key=True),
    sa.Column("retailer_id", sa.ForeignKey("retailers.id"), primary_key=True),
    sa.Column("raw_name", sa.Text, nullable=False),
)
prices_current = sa.Table(
    "prices_current",
    metadata,
    sa.Column("format_id", sa.ForeignKey("retail_formats.id"), primary_key=True),
    sa.Column("barcode", sa.ForeignKey("products.barcode"), primary_key=True),
    sa.Column("regular", sa.Integer, nullable=False),
    sa.Column("discounted", sa.Integer),
    sa.Column("disc_from", sa.Date),
    sa.Column("disc_to", sa.Date),
    sa.Column("unit_price", sa.Integer, nullable=False),
    sa.Column("vat", sa.Integer, nullable=False),
    sa.Column("list_date", sa.Date, nullable=False),
    sa.Column(
        "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
    ),
    sa.CheckConstraint("regular >= 0 AND unit_price >= 0"),
    sa.CheckConstraint("discounted IS NULL OR discounted BETWEEN 0 AND regular"),
)
price_changes = sa.Table(
    "price_changes",
    metadata,
    sa.Column("format_id", sa.ForeignKey("retail_formats.id"), primary_key=True),
    sa.Column("barcode", sa.ForeignKey("products.barcode"), primary_key=True),
    sa.Column("changed_on", sa.Date, primary_key=True),
    sa.Column("regular", sa.Integer, nullable=False),
    sa.Column("discounted", sa.Integer),
)
sa.Index("ix_price_changes_date", price_changes.c.changed_on)
monthly_snapshots = sa.Table(
    "monthly_snapshots",
    metadata,
    sa.Column("format_id", sa.ForeignKey("retail_formats.id"), primary_key=True),
    sa.Column("barcode", sa.ForeignKey("products.barcode"), primary_key=True),
    sa.Column("month", sa.Date, primary_key=True),
    sa.Column("regular", sa.Integer, nullable=False),
    sa.Column("discounted", sa.Integer),
)
ingest_runs = sa.Table(
    "ingest_runs",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True),
    sa.Column("retailer_id", sa.ForeignKey("retailers.id"), nullable=False),
    sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("http_status", sa.Integer),
    sa.Column("rows_total", sa.Integer, nullable=False),
    sa.Column("rows_valid", sa.Integer, nullable=False),
    sa.Column("errors_json", sa.JSON, nullable=False),
)
index_monthly = sa.Table(
    "index_monthly",
    metadata,
    sa.Column("month", sa.Date, primary_key=True),
    sa.Column("category_code", sa.ForeignKey("categories.code"), primary_key=True),
    sa.Column("value", sa.Numeric(12, 4), nullable=False),
    sa.Column("n_products", sa.Integer, nullable=False),
)


def database_url() -> str:
    load_dotenv()
    return (
        (os.environ.get("DATABASE_URL") or "postgresql+psycopg://korpa:korpa@localhost:5432/korpa")
        .replace("postgres://", "postgresql+psycopg://", 1)
        .replace("postgresql://", "postgresql+psycopg://", 1)
    )
