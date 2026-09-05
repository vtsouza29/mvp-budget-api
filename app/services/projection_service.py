"""Project recurring charges forward over a window of months."""

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal

from app.core.cache import Cache
from app.core.enums import SpendCategory
from app.schemas.common import to_money
from app.schemas.projection import (
    MonthlyProjection,
    ProjectedCharge,
    ProjectionRequest,
    ProjectionResponse,
    ProjectionSubscription,
)

CACHE_NAMESPACE = "projection"


def month_index(year: int, month: int) -> int:
    """Map a calendar month onto a single ordinal, so arithmetic is trivial."""
    return year * 12 + (month - 1)


def month_label(index: int) -> str:
    year, month = divmod(index, 12)
    return f"{year:04d}-{month + 1:02d}"


def parse_month(label: str) -> int:
    year, month = label.split("-")
    return month_index(int(year), int(month))


class ProjectionService:
    """Pure calculation: no persistence, only the cache in front of it."""

    def __init__(self, cache: Cache, ttl_seconds: int) -> None:
        self._cache = cache
        self._ttl_seconds = ttl_seconds

    async def project(self, request: ProjectionRequest) -> ProjectionResponse:
        cache_key = self._cache_key(request)

        cached = await self._cache.get(cache_key)
        if cached is not None:
            return ProjectionResponse.model_validate({**cached, "cached": True})

        response = self._compute(request)
        await self._cache.set(cache_key, response.model_dump(mode="json"), self._ttl_seconds)
        return response

    def _compute(self, request: ProjectionRequest) -> ProjectionResponse:
        start = parse_month(request.start_month) if request.start_month else _current_month_index()
        end = start + request.months

        buckets: dict[int, list[ProjectedCharge]] = {index: [] for index in range(start, end)}

        for subscription in request.subscriptions:
            for index in self._charge_months(subscription, start, end):
                buckets[index].append(
                    ProjectedCharge(
                        name=subscription.name,
                        category=subscription.category,
                        amount_brl=to_money(subscription.amount_brl),
                    )
                )

        timeline: list[MonthlyProjection] = []
        overall_by_category: dict[SpendCategory, Decimal] = {}
        total = Decimal("0")

        for index in range(start, end):
            charges = buckets[index]
            by_category: dict[SpendCategory, Decimal] = {}
            month_total = Decimal("0")

            for charge in charges:
                amount = Decimal(str(charge.amount_brl))
                month_total += amount
                by_category[charge.category] = by_category.get(charge.category, Decimal("0")) + amount
                overall_by_category[charge.category] = (
                    overall_by_category.get(charge.category, Decimal("0")) + amount
                )

            total += month_total
            timeline.append(
                MonthlyProjection(
                    month=month_label(index),
                    total_brl=to_money(month_total),
                    by_category={key: to_money(value) for key, value in sorted(by_category.items())},
                    charges=sorted(charges, key=lambda item: item.name.lower()),
                )
            )

        heaviest = max(timeline, key=lambda month: month.total_brl)

        return ProjectionResponse(
            start_month=month_label(start),
            months=request.months,
            total_brl=to_money(total),
            monthly_average_brl=to_money(total / request.months),
            heaviest_month=heaviest.month,
            by_category={
                key: to_money(value) for key, value in sorted(overall_by_category.items())
            },
            timeline=timeline,
            cached=False,
        )

    @staticmethod
    def _charge_months(subscription: ProjectionSubscription, start: int, end: int) -> list[int]:
        """Months inside [start, end) in which this subscription is charged.

        A renewal date already in the past is rolled forward by whole cycles, so
        a yearly plan renewed last March still lands on March of the window.
        """
        step = subscription.billing_cycle.month_step
        renewal = month_index(
            subscription.next_renewal_on.year, subscription.next_renewal_on.month
        )

        if renewal < start:
            missed_cycles = -(-(start - renewal) // step)  # divisão inteira para cima
            renewal += missed_cycles * step

        return list(range(renewal, end, step)) if renewal < end else []

    @staticmethod
    def _cache_key(request: ProjectionRequest) -> str:
        payload = json.dumps(request.model_dump(mode="json"), sort_keys=True)
        return f"{CACHE_NAMESPACE}:{hashlib.sha256(payload.encode()).hexdigest()}"


def _current_month_index() -> int:
    today = datetime.now(timezone.utc).date()
    return month_index(today.year, today.month)
