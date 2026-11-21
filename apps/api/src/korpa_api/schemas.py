from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Barcode = Annotated[str, Field(pattern=r"^[0-9]{13}$", min_length=13, max_length=13, strict=True)]


class Problem(BaseModel):
    type: str = "about:blank"
    title: str
    status: int = Field(ge=100, le=599)
    detail: str
    instance: str
    errors: list[dict[str, str | list[str | int]]] | None = None


class SearchParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    q: str = Field(min_length=2, max_length=100)
    category: int | None = Field(default=None, ge=1, le=25)
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0, le=1000)

    @field_validator("q")
    @classmethod
    def nonblank_query(cls, value: str) -> str:
        if len(value.strip()) < 2:
            raise ValueError("Query must contain at least two non-padding characters")
        return value.strip()


class SearchItem(BaseModel):
    barcode: str
    name: str
    brand: str
    unit: str
    category_code: int
    min_effective_para: int | None
    max_effective_para: int | None
    n_formats: int
    any_discount: bool
    list_date: date | None


class SearchResponse(BaseModel):
    items: list[SearchItem]
    total: int
    as_of: date


class BasketItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    barcode: Barcode
    qty: int = Field(ge=1, le=99, strict=True)


class BasketRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[BasketItem] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def merge_duplicates(self) -> "BasketRequest":
        quantities: dict[str, int] = {}
        for item in self.items:
            quantities[item.barcode] = quantities.get(item.barcode, 0) + item.qty
        if any(qty > 99 for qty in quantities.values()):
            raise ValueError("Merged quantity must not exceed 99 per barcode")
        self.items = [BasketItem(barcode=barcode, qty=qty) for barcode, qty in quantities.items()]
        return self


class BasketFormat(BaseModel):
    id: int
    name: str
    total_para: int
    found_barcodes: list[str]
    missing_barcodes: list[str]
    complete: bool
    rank: int
    list_date_min: date | None
    list_date_max: date | None


class BasketRetailer(BaseModel):
    id: int
    name: str
    slug: str
    formats: list[BasketFormat]


class BasketResponse(BaseModel):
    retailers: list[BasketRetailer]
    as_of: date


class CategoryItem(BaseModel):
    code: int
    name: str
    n_products: int


class QualityItem(BaseModel):
    id: int
    name: str
    slug: str
    status: Literal["ok", "partial", "failed", "never"]
    http_status: int | None
    rows_total: int | None
    rows_valid: int | None
    errors: dict[str, int]
    errors_by_rule: dict[str, int]
    deviations: dict[str, int]
    profile: str | None
    finished_at: datetime | None
    list_date: date | None
    days_since_list_date: int | None


class QualityResponse(BaseModel):
    retailers: list[QualityItem]
    as_of: date
