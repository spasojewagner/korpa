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
    q: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        description="Text query; required unless category is supplied.",
    )
    category: int | None = Field(default=None, ge=1, le=25)
    limit: int = Field(default=20, ge=1, le=50)
    offset: int = Field(default=0, ge=0, le=1000)

    @field_validator("q")
    @classmethod
    def nonblank_query(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if len(value.strip()) < 2:
            raise ValueError("Query must contain at least two non-padding characters")
        return value.strip()

    @model_validator(mode="after")
    def require_query_or_category(self) -> "SearchParams":
        if self.q is None and self.category is None:
            raise ValueError("At least one of q or category is required")
        return self


class SearchItem(BaseModel):
    barcode: str
    name: str
    brand: str
    unit: str
    category_code: int
    min_effective_para: int
    max_effective_para: int
    n_formats: int
    any_discount: bool
    list_date: date


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
    suspected_errors: dict[str, int]
    errors_by_rule: dict[str, int]
    deviations: dict[str, int]
    profile: str | None
    finished_at: datetime | None
    list_date: date | None
    days_since_list_date: int | None


class QualityResponse(BaseModel):
    retailers: list[QualityItem]
    as_of: date


class IndexPoint(BaseModel):
    month: date
    value: float | None = Field(allow_inf_nan=False)
    n_products: int = Field(ge=0)
    n_excluded: int = Field(ge=0)
    provisional: bool


class IndexCategory(BaseModel):
    code: int = Field(ge=0, le=25)
    name: str
    points: list[IndexPoint]


class IndexResponse(BaseModel):
    as_of: date
    base_month: date
    categories: list[IndexCategory] = Field(max_length=26)


class SignalsParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["jump", "outlier"] | None = None
    limit: int = Field(default=100, ge=1, le=200)


class SignalItem(BaseModel):
    type: Literal["jump", "outlier"]
    barcode: Barcode
    name: str
    retailer: str
    format: str
    date: date
    price_para: int = Field(ge=0)
    reference_para: int = Field(gt=0)
    ratio: float = Field(allow_inf_nan=False)


class SignalsResponse(BaseModel):
    as_of: date
    items: list[SignalItem] = Field(max_length=200)


class AiBasketRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sentence: str = Field(min_length=3, max_length=300)


class AiBasketItem(BaseModel):
    phrase: str
    query: str
    qty: int
    proposed: bool = Field(
        description="Suggested by the model for a goal, not named by the shopper"
    )
    candidates: list[SearchItem]


class AiBasketResponse(BaseModel):
    as_of: date
    model: str
    items: list[AiBasketItem]
    budget_para: int | None = Field(description="Budget the shopper stated, if any")


class AiStatus(BaseModel):
    enabled: bool
