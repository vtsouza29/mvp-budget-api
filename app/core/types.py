"""Custom SQLAlchemy column types."""

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import Integer
from sqlalchemy.types import TypeDecorator

_CENTS = Decimal("0.01")


class MoneyType(TypeDecorator):
    """Store a monetary amount as an integer number of cents.

    SQLite has no native decimal type, so persisting ``Numeric`` there round-trips
    through float and loses precision. Cents keep the value exact and still sort
    correctly in ``ORDER BY``.
    """

    impl = Integer
    cache_ok = True

    def process_bind_param(self, value: Decimal | None, dialect) -> int | None:
        if value is None:
            return None
        quantized = Decimal(value).quantize(_CENTS, rounding=ROUND_HALF_UP)
        return int(quantized * 100)

    def process_result_value(self, value: int | None, dialect) -> Decimal | None:
        if value is None:
            return None
        return (Decimal(value) / 100).quantize(_CENTS)
