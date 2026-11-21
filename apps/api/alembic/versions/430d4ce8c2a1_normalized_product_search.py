"""Normalized full-text search and barcode price lookups."""

import sqlalchemy as sa
from alembic import op

revision = "430d4ce8c2a1"
down_revision = "21b48c0f6e20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute("""
        CREATE FUNCTION public.korpa_norm(value text) RETURNS text
        LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
        SET search_path = '' AS $$
            SELECT public.unaccent('public.unaccent'::regdictionary,
                                   replace(lower(value), 'đ', 'dj'))
        $$
    """)
    op.add_column(
        "products",
        sa.Column(
            "search_norm",
            sa.Text(),
            sa.Computed("korpa_norm(name || ' ' || brand)", persisted=True),
        ),
    )
    op.create_index(
        "ix_products_search_norm_trgm",
        "products",
        ["search_norm"],
        postgresql_using="gin",
        postgresql_ops={"search_norm": "gin_trgm_ops"},
    )
    op.create_index("ix_prices_current_barcode", "prices_current", ["barcode"])
    op.execute("""
        CREATE FUNCTION public.korpa_products_search() RETURNS trigger
        LANGUAGE plpgsql SET search_path = '' AS $$
        BEGIN
            NEW.search_tsv := to_tsvector('simple'::regconfig,
                public.korpa_norm(NEW.name || ' ' || NEW.brand));
            RETURN NEW;
        END $$
    """)
    op.execute("""
        CREATE TRIGGER products_search_refresh
        BEFORE INSERT OR UPDATE OF name, brand, search_tsv ON products
        FOR EACH ROW EXECUTE FUNCTION public.korpa_products_search()
    """)
    op.execute("UPDATE products SET search_tsv = to_tsvector('simple', search_norm)")


def downgrade() -> None:
    op.execute("DROP TRIGGER products_search_refresh ON products")
    op.execute("DROP FUNCTION public.korpa_products_search()")
    op.drop_index("ix_prices_current_barcode", table_name="prices_current")
    op.drop_index("ix_products_search_norm_trgm", table_name="products")
    op.drop_column("products", "search_norm")
    op.execute("DROP FUNCTION public.korpa_norm(text)")
