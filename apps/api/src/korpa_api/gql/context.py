import asyncio
from collections import defaultdict
from collections.abc import Sequence
from datetime import date, timedelta

import sqlalchemy as sa
from korpa_ingest import db
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select
from strawberry.dataloader import DataLoader
from strawberry.fastapi import BaseContext

from korpa_api.pricing import belgrade_today, effective_price

FORMAT_CAP = 60
NAME_CAP = 50
OBSERVATION_CAP = 1000


def month_start(as_of: date, months: int) -> date:
    ordinal = as_of.year * 12 + as_of.month - months
    return date(ordinal // 12, ordinal % 12 + 1, 1)


class Context(BaseContext):
    def __init__(self, session: AsyncSession, as_of: date | None = None) -> None:
        super().__init__()
        self.session = session
        self.as_of = as_of or belgrade_today()
        self.lock = asyncio.Lock()
        self.products = DataLoader(load_fn=self.load_products, max_batch_size=50)
        self.prices = DataLoader(load_fn=self.load_prices, max_batch_size=50)
        self.formats = DataLoader(load_fn=self.load_formats)
        self.retailers = DataLoader(load_fn=self.load_retailers)
        self.categories = DataLoader(load_fn=self.load_categories)
        self.names = DataLoader(load_fn=self.load_names, max_batch_size=50)
        self.history = DataLoader(load_fn=self.load_history, max_batch_size=50)
        self.changes = DataLoader(load_fn=self.load_changes, max_batch_size=50)

    async def rows(self, statement: Select[*tuple[object, ...]]) -> list[RowMapping]:
        # DataLoader batches may run concurrently; an AsyncSession must not.
        async with self.lock:
            return list((await self.session.execute(statement)).mappings())

    async def load_products(self, keys: list[str]) -> Sequence[RowMapping | None]:
        rows = await self.rows(sa.select(db.products).where(db.products.c.barcode.in_(keys)))
        indexed = {row["barcode"]: row for row in rows}
        return [indexed.get(key) for key in keys]

    async def dimension(self, table: sa.Table, key: str, keys: list[int]) -> list[RowMapping]:
        rows = await self.rows(sa.select(table).where(table.c[key].in_(keys)))
        indexed = {row[key]: row for row in rows}
        return [indexed[k] for k in keys]

    async def load_formats(self, keys: list[int]) -> list[RowMapping]:
        return await self.dimension(db.retail_formats, "id", keys)

    async def load_retailers(self, keys: list[int]) -> list[RowMapping]:
        return await self.dimension(db.retailers, "id", keys)

    async def load_categories(self, keys: list[int]) -> list[RowMapping]:
        return await self.dimension(db.categories, "code", keys)

    async def grouped(
        self,
        statement: Select[*tuple[object, ...]],
        keys: list[str],
        cap: int,
    ) -> list[list[RowMapping] | BaseException]:
        result: dict[str, list[RowMapping]] = defaultdict(list)
        for row in await self.rows(statement):
            result[row["barcode"]].append(row)
        return [
            ValueError(f"Result exceeds the {cap}-record limit for this field")
            if len(result[key]) > cap
            else result[key]
            for key in keys
        ]

    async def load_prices(self, keys: list[str]) -> list[list[RowMapping] | BaseException]:
        p = db.prices_current
        ranked = (
            sa.select(
                p,
                effective_price(
                    p.c.regular, p.c.discounted, p.c.disc_from, p.c.disc_to, self.as_of
                ).label("effective_para"),
                sa.func.row_number()
                .over(partition_by=p.c.barcode, order_by=p.c.format_id)
                .label("position"),
            )
            .where(p.c.barcode.in_(keys))
            .subquery()
        )
        return await self.grouped(
            sa.select(ranked)
            .where(
                ranked.c.position <= FORMAT_CAP + 1,
            )
            .order_by(ranked.c.barcode, ranked.c.position),
            keys,
            FORMAT_CAP,
        )

    async def load_names(self, keys: list[str]) -> list[list[RowMapping] | BaseException]:
        p = db.product_names
        ranked = (
            sa.select(
                p,
                sa.func.row_number()
                .over(
                    partition_by=p.c.barcode,
                    order_by=p.c.retailer_id,
                )
                .label("position"),
            )
            .where(p.c.barcode.in_(keys))
            .subquery()
        )
        return await self.grouped(
            sa.select(ranked)
            .where(
                ranked.c.position <= NAME_CAP + 1,
            )
            .order_by(ranked.c.barcode, ranked.c.position),
            keys,
            NAME_CAP,
        )

    async def observations(
        self,
        table: sa.Table,
        time_column: str,
        keys: list[tuple[str, int]],
        monthly: bool,
    ) -> list[list[RowMapping] | BaseException]:
        maximum = max(value for _, value in keys)
        cutoff = (
            month_start(self.as_of, maximum)
            if monthly
            else (self.as_of - timedelta(days=maximum - 1))
        )
        cap = min(maximum * FORMAT_CAP, OBSERVATION_CAP)
        codes = list(dict.fromkeys(code for code, _ in keys))
        ranked = (
            sa.select(
                table,
                sa.func.row_number()
                .over(
                    partition_by=table.c.barcode,
                    order_by=[table.c[time_column].desc(), table.c.format_id],
                )
                .label("position"),
            )
            .where(
                table.c.barcode.in_(codes),
                table.c[time_column] >= cutoff,
                table.c[time_column] <= self.as_of,
            )
            .subquery()
        )
        grouped = await self.grouped(
            sa.select(ranked)
            .where(ranked.c.position <= cap + 1)
            .order_by(ranked.c.barcode, ranked.c.position),
            codes,
            cap,
        )
        by_code = dict(zip(codes, grouped, strict=True))
        results: list[list[RowMapping] | BaseException] = []
        for code, value in keys:
            records = by_code[code]
            if isinstance(records, BaseException):
                results.append(records)
                continue
            start = (
                month_start(self.as_of, value)
                if monthly
                else (self.as_of - timedelta(days=value - 1))
            )
            subset = [row for row in records if row[time_column] >= start]
            results.append(
                ValueError("History result exceeds the field record limit")
                if len(subset) > min(value * FORMAT_CAP, OBSERVATION_CAP)
                else subset
            )
        return results

    async def load_history(
        self, keys: list[tuple[str, int]]
    ) -> list[list[RowMapping] | BaseException]:
        return await self.observations(db.monthly_snapshots, "month", keys, True)

    async def load_changes(
        self, keys: list[tuple[str, int]]
    ) -> list[list[RowMapping] | BaseException]:
        return await self.observations(db.price_changes, "changed_on", keys, False)
