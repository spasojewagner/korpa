from datetime import date, datetime
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from sqlalchemy.sql.elements import ColumnElement

from korpa_api.schemas import BasketItem, BasketSplit, BasketSplitItem


def belgrade_today() -> date:
    return datetime.now(ZoneInfo("Europe/Belgrade")).date()


def split_basket(
    items: list[BasketItem], offers: list[BasketSplitItem], best_total: int | None
) -> BasketSplit | None:
    """Choose unit-price minima, with format name/id breaking ties consistently.

    The store count describes the chosen formats, not a minimum-store route optimizer.
    """
    cheapest: dict[str, BasketSplitItem] = {}
    for offer in offers:
        current = cheapest.get(offer.barcode)
        if current is None or (offer.price_para, offer.format.name, offer.format.id) < (
            current.price_para,
            current.format.name,
            current.format.id,
        ):
            cheapest[offer.barcode] = offer
    if any(item.barcode not in cheapest for item in items):
        return None
    chosen = [cheapest[item.barcode] for item in items]
    total = sum(cheapest[item.barcode].price_para * item.qty for item in items)
    return BasketSplit(
        total_para=total,
        saving_vs_best_para=None if best_total is None else best_total - total,
        n_formats=len({offer.format.id for offer in chosen}),
        items=chosen,
    )


def effective_price(
    regular: ColumnElement[int],
    discounted: ColumnElement[int | None],
    disc_from: ColumnElement[date | None],
    disc_to: ColumnElement[date | None],
    as_of: date,
) -> ColumnElement[int]:
    """Shared expression for REST aggregates and future nested price reads."""
    active = sa.and_(
        discounted.is_not(None),
        sa.or_(disc_from.is_(None), disc_from <= as_of),
        sa.or_(disc_to.is_(None), disc_to >= as_of),
    )
    return sa.cast(sa.case((active, discounted), else_=regular), sa.Integer)
