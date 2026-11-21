from datetime import date, datetime
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from sqlalchemy.sql.elements import ColumnElement


def belgrade_today() -> date:
    return datetime.now(ZoneInfo("Europe/Belgrade")).date()


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
