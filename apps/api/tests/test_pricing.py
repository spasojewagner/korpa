from datetime import date

import pytest
import sqlalchemy as sa
from korpa_api.pricing import effective_price, split_basket
from korpa_api.schemas import BasketItem, BasketSplitFormat, BasketSplitItem

DAY = date(2026, 11, 21)
B1, B2 = "0000000000001", "0000000000002"


def offer(barcode: str, price: int, id: int, name: str = "Market") -> BasketSplitItem:
    return BasketSplitItem(
        barcode=barcode,
        price_para=price,
        format=BasketSplitFormat(id=id, name=name),
        list_date=DAY,
    )


def test_split_ties_are_stable_and_quantities_are_applied() -> None:
    items = [BasketItem(barcode=B1, qty=3), BasketItem(barcode=B2, qty=2)]
    offers = [offer(B1, 10, 3, "B"), offer(B1, 10, 2, "A"), offer(B1, 10, 1, "A"), offer(B2, 0, 4)]
    result = split_basket(items, offers, 80)
    assert result is not None
    assert result.total_para == 30
    assert result.saving_vs_best_para == 50
    assert result.n_formats == 2
    assert [item.format.id for item in result.items] == [1, 4]
    assert result == split_basket(items, list(reversed(offers)), 80)


def test_split_missing_item_and_no_complete_single_format() -> None:
    items = [BasketItem(barcode=B1, qty=1), BasketItem(barcode=B2, qty=1)]
    assert split_basket(items, [offer(B1, 10, 1)], None) is None
    assert split_basket(items, [], None) is None
    result = split_basket(items, [offer(B1, 10, 1), offer(B2, 20, 2)], None)
    assert result is not None
    assert result.total_para == 30
    assert result.saving_vs_best_para is None


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (DAY, DAY, 50),
        (None, None, 50),
        (date(2026, 11, 22), None, 75),
        (None, date(2026, 11, 20), 75),
    ],
)
def test_split_compares_effective_discount_with_regular_price(
    start: date | None,
    end: date | None,
    expected: int,
) -> None:
    # Execute the shared price expression without requiring the PostgreSQL fixture.
    engine = sa.create_engine("sqlite://")
    with engine.connect() as connection:
        price = connection.scalar(
            sa.select(
                effective_price(
                    sa.literal(100),
                    sa.literal(50),
                    sa.literal(start, type_=sa.Date),
                    sa.literal(end, type_=sa.Date),
                    DAY,
                )
            )
        )
    engine.dispose()
    assert price is not None
    result = split_basket(
        [BasketItem(barcode=B1, qty=1)], [offer(B1, price, 1), offer(B1, 75, 2)], expected
    )
    assert result is not None
    assert result.total_para == expected
    assert result.saving_vs_best_para == 0
    assert result.n_formats == 1
