"""Reproducible, isolated API benchmark over real loopback HTTP requests."""

import json
import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Annotated

import httpx
import sqlalchemy as sa
import typer
from korpa_ingest import db
from korpa_ingest.store import month_start
from sqlalchemy.engine import Engine

from korpa_api.analytics import refresh_index
from korpa_api.pricing import belgrade_today
from korpa_api.repository import basket_statement, search_statements
from korpa_api.schemas import BasketRequest, SearchParams

app = typer.Typer()


def benchmark_engine() -> Engine:
    url = db.database_url()
    if sa.engine.make_url(url).database != "korpa_bench":
        raise typer.BadParameter("DATABASE_URL must name the dedicated korpa_bench database")
    return sa.create_engine(url)


@app.command()
def seed() -> None:
    """Replace only the dedicated benchmark database's synthetic data."""
    engine = benchmark_engine()
    subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "apps/api/alembic.ini",
            "upgrade",
            "head",
        ],
        check=True,
    )
    with engine.begin() as c:
        for table in reversed(db.metadata.sorted_tables):
            c.execute(table.delete())
        c.execute(
            sa.text("""
            INSERT INTO categories (code, name)
            SELECT i, 'Probna kategorija ' || i FROM generate_series(1, 25) i
        """)
        )
        c.execute(
            sa.text("""
            INSERT INTO retailers (id, name, slug, dataset_id, resource_url)
            SELECT i, 'Probni trgovac ' || i, 'bench-' || i, 'synthetic-' || i,
                'https://example.org/synthetic/' || i FROM generate_series(1, 10) i
        """)
        )
        c.execute(
            sa.text("""
            INSERT INTO retail_formats (id, retailer_id, name)
            SELECT i, (i - 1) / 6 + 1, 'Probni format ' || i FROM generate_series(1, 60) i
        """)
        )
        c.execute(
            sa.text("""
            INSERT INTO products (barcode, name, brand, unit, category_code)
            SELECT lpad(i::text, 13, '0'),
                (ARRAY['Mleko', 'Čokolada', 'Đus', 'Hleb', 'Jabuka', 'Jogurt', 'Kafa',
                       'Pirinač', 'Ulje', 'Testenina'])[1 + ((i - 1) % 10)] || ' ' || i,
                'Probni brend ' || (i % 20), 'kom', (i % 25) + 1
            FROM generate_series(1, 12000) i
        """)
        )
        c.execute(
            sa.text("""
            INSERT INTO prices_current
                (format_id, barcode, regular, discounted, disc_from, disc_to, unit_price,
                 vat, list_date)
            SELECT f.id, p.barcode, 10000 + p.barcode::bigint % 1000 + f.id,
                CASE WHEN f.id % 3 = 0 THEN 9900 + p.barcode::bigint % 1000 + f.id END,
                CASE WHEN f.id % 3 = 0 THEN :today - 1 END,
                CASE WHEN f.id % 3 = 0 THEN :today + 1 END,
                10000 + p.barcode::bigint % 1000 + f.id, 20, :today
            FROM products p CROSS JOIN retail_formats f
        """),
            {"today": belgrade_today()},
        )
    with engine.begin() as c:
        c.execute(
            sa.text("""
            INSERT INTO monthly_prices
                (barcode, month, min_regular, median_regular, max_regular, n_formats)
            SELECT barcode, m.month, min(regular),
                   percentile_disc(0.5) WITHIN GROUP (ORDER BY regular), max(regular), count(*)
            FROM prices_current CROSS JOIN
                (VALUES (CAST(:base AS date)), (CAST(:next AS date))) AS m(month)
            GROUP BY barcode, m.month
        """),
            {"base": month_start(belgrade_today(), 2), "next": month_start(belgrade_today(), 1)},
        )
    with engine.begin() as c:
        c.execute(
            sa.text("""
            INSERT INTO price_changes (format_id, barcode, changed_on, regular)
            SELECT 60, barcode, :today - 10, regular FROM prices_current
            WHERE format_id = 60 AND barcode::bigint <= 100
            UNION ALL
            SELECT 60, barcode, :today, regular * 2 FROM prices_current
            WHERE format_id = 60 AND barcode::bigint <= 100
        """),
            {"today": belgrade_today()},
        )
        c.execute(
            sa.text("""
            UPDATE prices_current SET regular = regular * 2,
                discounted = NULL, disc_from = NULL, disc_to = NULL
            WHERE format_id = 60 AND barcode::bigint <= 100
        """)
        )
    refresh_index(engine, belgrade_today())
    with engine.begin() as c:
        c.exec_driver_sql("ANALYZE price_changes")
        c.exec_driver_sql("ANALYZE monthly_prices")
        c.exec_driver_sql("ANALYZE index_monthly")
        c.exec_driver_sql("ANALYZE products")
        c.exec_driver_sql("ANALYZE prices_current")
        c.exec_driver_sql("ANALYZE retail_formats")
        c.exec_driver_sql("ANALYZE retailers")
        size = c.scalar(sa.text("SELECT pg_database_size(current_database())"))
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as c:
        c.exec_driver_sql("VACUUM ANALYZE prices_current")
    engine.dispose()
    typer.echo(
        json.dumps(
            {"products": 12000, "formats": 60, "prices_current": 720000, "database_bytes": size}
        )
    )


@app.command()
def measure(
    samples: Annotated[int, typer.Option(min=20, max=500)] = 50,
    output: Annotated[Path, typer.Option()] = Path("docs/bench"),
) -> None:
    """Measure the entire API request path, including loopback TCP and serialization."""
    engine = benchmark_engine()
    output.mkdir(parents=True, exist_ok=True)
    port = 8765
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "korpa_api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--no-access-log",
            "--log-level",
            "error",
        ],
        stdout=subprocess.DEVNULL,
    )
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=30) as client:
            for _ in range(100):
                try:
                    if client.get("/health").status_code == 200:
                        break
                except httpx.ConnectError:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Benchmark server did not start")
            basket = {"items": [{"barcode": f"{i:013d}", "qty": 1} for i in range(1, 21)]}
            timings: dict[str, list[float]] = {
                "search": [],
                "basket_20": [],
                "index": [],
                "signals_200": [],
            }
            for i in range(samples + 10):
                start = time.perf_counter()
                result = client.get(
                    "/api/search", params={"q": ["mleko", "cokolada", "cokolda"][i % 3]}
                )
                result.raise_for_status()
                search_ms = (time.perf_counter() - start) * 1000
                start = time.perf_counter()
                result = client.post("/api/basket", json=basket)
                result.raise_for_status()
                basket_ms = (time.perf_counter() - start) * 1000
                start = time.perf_counter()
                result = client.get("/api/index")
                result.raise_for_status()
                index_ms = (time.perf_counter() - start) * 1000
                start = time.perf_counter()
                result = client.get("/api/signals", params={"limit": 200})
                result.raise_for_status()
                signals_ms = (time.perf_counter() - start) * 1000
                if len(result.json()["items"]) != 200:
                    raise RuntimeError("Benchmark signals fixture is missing")
                if i >= 10:
                    timings["search"].append(search_ms)
                    timings["basket_20"].append(basket_ms)
                    timings["index"].append(index_ms)
                    timings["signals_200"].append(signals_ms)
        results = {
            key: {
                "p95_ms": round(sorted(values)[math.ceil(len(values) * 0.95) - 1], 3),
                "median_ms": round(sorted(values)[len(values) // 2], 3),
            }
            for key, values in timings.items()
        }
        report = {
            "measured_on": belgrade_today().isoformat(),
            "samples": samples,
            "warmups": 10,
            "transport": "loopback HTTP, complete JSON responses",
            "products": 12000,
            "formats": 60,
            "prices_current": 720000,
            "monthly_prices": 24000,
            "price_changes": 200,
            "signals_limit": 200,
            "results": results,
        }
        (output / "rest-latency.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        params = SearchParams(q="cokolda")
        count, items = search_statements(params, belgrade_today())
        plans: list[str] = []
        with engine.connect() as c:
            c.exec_driver_sql("SET pg_trgm.word_similarity_threshold = 0.3")
            for name, statement in (("Count", count), ("Page and price aggregation", items)):
                compiled = statement.compile(
                    dialect=engine.dialect, compile_kwargs={"literal_binds": True}
                )
                # Keep dialect escaping for DBAPI percent operators.
                sql = str(compiled)
                plan = c.exec_driver_sql("EXPLAIN (ANALYZE, BUFFERS) " + sql)
                plans.append(name + "\n" + "\n".join(str(row[0]) for row in plan))
            basket_query = basket_statement(BasketRequest.model_validate(basket), belgrade_today())
            compiled = basket_query.compile(
                dialect=engine.dialect, compile_kwargs={"literal_binds": True}
            )
            plan = c.exec_driver_sql("EXPLAIN (ANALYZE, BUFFERS) " + str(compiled))
            plans.append("Basket query (20 items)\n" + "\n".join(str(row[0]) for row in plan))
        (output / "search-explain.txt").write_text("\n\n".join(plans) + "\n", encoding="utf-8")
        typer.echo(json.dumps(report, indent=2))
    finally:
        server.terminate()
        server.wait(timeout=10)
        engine.dispose()


if __name__ == "__main__":
    app()
