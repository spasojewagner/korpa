"""Read-only GraphQL timings against the dedicated synthetic benchmark database."""

import json
import math
import subprocess
import sys
import time
from pathlib import Path

import httpx
import sqlalchemy as sa

from korpa_api.bench import benchmark_engine
from korpa_api.pricing import belgrade_today

QUERY = """
query Benchmark($codes: [String!]!) {
  products(barcodes: $codes) {
    barcode
    prices { format { retailer { name } } }
    history(months: 1) { month }
  }
}
"""


def measure() -> None:
    engine = benchmark_engine()
    with engine.connect() as connection:
        counts = {
            name: connection.scalar(sa.text(f"SELECT count(*) FROM {name}"))
            for name in ("products", "retail_formats", "prices_current", "monthly_snapshots")
        }
    engine.dispose()
    port = 8766
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
    timings: dict[str, list[float]] = {}
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
            for size in (1, 20):
                samples = timings[f"products_{size}"] = []
                for iteration in range(60):
                    start = time.perf_counter()
                    response = client.post(
                        "/graphql",
                        json={
                            "query": QUERY,
                            "variables": {"codes": [f"{n:013d}" for n in range(1, size + 1)]},
                        },
                    )
                    response.raise_for_status()
                    if response.json().get("errors"):
                        raise RuntimeError(response.text)
                    assert len(response.json()["data"]["products"]) == size
                    if iteration >= 10:
                        samples.append((time.perf_counter() - start) * 1000)
        report = {
            "measured_on": belgrade_today().isoformat(),
            "samples": 50,
            "warmups": 10,
            "transport": "loopback HTTP, complete JSON responses",
            "rows": counts,
            "query": QUERY.strip(),
            "results": {
                key: {
                    "p95_ms": round(sorted(values)[math.ceil(len(values) * 0.95) - 1], 3),
                    "median_ms": round(sorted(values)[len(values) // 2], 3),
                }
                for key, values in timings.items()
            },
        }
        destination = Path("docs/bench/graphql-latency.json")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
    finally:
        server.terminate()
        server.wait(timeout=10)


if __name__ == "__main__":
    measure()
