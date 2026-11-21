from datetime import date
from typing import Annotated

import sqlalchemy as sa
import strawberry
from pydantic import BaseModel, Field
from sqlalchemy.engine import RowMapping
from strawberry.types import Info

from korpa_api.gql.context import Context
from korpa_api.schemas import Barcode

GraphInfo = Info[Context, None]


class ProductInput(BaseModel):
    barcode: Barcode


class ProductsInput(BaseModel):
    barcodes: list[Barcode] = Field(min_length=1, max_length=50)


class MonthsInput(BaseModel):
    months: Annotated[int, Field(ge=1, le=24, strict=True)]


class DaysInput(BaseModel):
    days: Annotated[int, Field(ge=1, le=120, strict=True)]


@strawberry.type
class Retailer:
    id: int
    name: str
    slug: str


def retailer(row: RowMapping) -> Retailer:
    return Retailer(id=row["id"], name=row["name"], slug=row["slug"])


@strawberry.type
class Format:
    id: int
    name: str
    retailer_id: strawberry.Private[int]

    @strawberry.field
    async def retailer(self, info: GraphInfo) -> Retailer:
        return retailer(await info.context.retailers.load(self.retailer_id))


def retail_format(row: RowMapping) -> Format:
    return Format(id=row["id"], name=row["name"], retailer_id=row["retailer_id"])


@strawberry.type
class Category:
    code: int
    name: str


@strawberry.type
class PublishedName:
    raw_name: str
    retailer_id: strawberry.Private[int]

    @strawberry.field
    async def retailer(self, info: GraphInfo) -> Retailer:
        return retailer(await info.context.retailers.load(self.retailer_id))


@strawberry.type
class Price:
    regular_para: int
    discounted_para: int | None
    effective_para: int
    unit_price_para: int
    vat: int
    discount_from: date | None
    discount_to: date | None
    list_date: date
    as_of: date
    format_id: strawberry.Private[int]

    @strawberry.field
    async def format(self, info: GraphInfo) -> Format:
        return retail_format(await info.context.formats.load(self.format_id))


def price(row: RowMapping, as_of: date) -> Price:
    return Price(
        regular_para=row["regular"],
        discounted_para=row["discounted"],
        effective_para=row["effective_para"],
        unit_price_para=row["unit_price"],
        vat=row["vat"],
        discount_from=row["disc_from"],
        discount_to=row["disc_to"],
        list_date=row["list_date"],
        as_of=as_of,
        format_id=row["format_id"],
    )


@strawberry.type
class Observation:
    regular_para: int
    discounted_para: int | None
    list_date: date
    as_of: date
    format_id: strawberry.Private[int]

    @strawberry.field
    async def format(self, info: GraphInfo) -> Format:
        return retail_format(await info.context.formats.load(self.format_id))


@strawberry.type
class MonthlySnapshot(Observation):
    month: date


@strawberry.type
class PriceChange(Observation):
    changed_on: date


@strawberry.type
class Product:
    barcode: str
    name: str
    brand: str
    unit: str
    category_code: strawberry.Private[int]

    @strawberry.field
    async def category(self, info: GraphInfo) -> Category:
        row = await info.context.categories.load(self.category_code)
        return Category(code=row["code"], name=row["name"])

    @strawberry.field
    async def names(self, info: GraphInfo) -> list[PublishedName]:
        return [
            PublishedName(raw_name=row["raw_name"], retailer_id=row["retailer_id"])
            for row in await info.context.names.load(self.barcode)
        ]

    @strawberry.field
    async def prices(self, info: GraphInfo) -> list[Price]:
        return [
            price(row, info.context.as_of) for row in await info.context.prices.load(self.barcode)
        ]

    @strawberry.field
    async def cheapest(self, info: GraphInfo) -> Price | None:
        rows = await info.context.prices.load(self.barcode)
        return (
            price(
                min(rows, key=lambda row: (row["effective_para"], row["format_id"])),
                info.context.as_of,
            )
            if rows
            else None
        )

    @strawberry.field
    async def history(self, info: GraphInfo, months: int = 12) -> list[MonthlySnapshot]:
        bound = MonthsInput(months=months).months
        return [
            MonthlySnapshot(
                regular_para=row["regular"],
                discounted_para=row["discounted"],
                month=row["month"],
                list_date=row["month"],
                as_of=info.context.as_of,
                format_id=row["format_id"],
            )
            for row in await info.context.history.load((self.barcode, bound))
        ]

    @strawberry.field
    async def changes(self, info: GraphInfo, days: int = 30) -> list[PriceChange]:
        bound = DaysInput(days=days).days
        return [
            PriceChange(
                regular_para=row["regular"],
                discounted_para=row["discounted"],
                changed_on=row["changed_on"],
                list_date=row["changed_on"],
                as_of=info.context.as_of,
                format_id=row["format_id"],
            )
            for row in await info.context.changes.load((self.barcode, bound))
        ]


def product(row: RowMapping) -> Product:
    return Product(
        barcode=row["barcode"],
        name=row["name"],
        brand=row["brand"],
        unit=row["unit"],
        category_code=row["category_code"],
    )


@strawberry.type
class Query:
    @strawberry.field
    def as_of(self, info: GraphInfo) -> date:
        return info.context.as_of

    @strawberry.field
    async def product(self, info: GraphInfo, barcode: str) -> Product | None:
        code = ProductInput(barcode=barcode).barcode
        row = await info.context.products.load(code)
        return product(row) if row is not None else None

    @strawberry.field
    async def products(self, info: GraphInfo, barcodes: list[str]) -> list[Product | None]:
        keys = ProductsInput(barcodes=barcodes).barcodes
        return [
            product(row) if row is not None else None
            for row in await info.context.products.load_many(keys)
        ]

    @strawberry.field
    async def categories(self, info: GraphInfo) -> list[Category]:
        from korpa_ingest import db

        rows = await info.context.rows(sa.select(db.categories).order_by(db.categories.c.code))
        for row in rows:
            info.context.categories.prime(row["code"], row)
        return [Category(code=row["code"], name=row["name"]) for row in rows]
