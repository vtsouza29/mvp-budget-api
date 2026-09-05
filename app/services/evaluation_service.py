"""Compare observed spending against the stored budgets."""

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal

from app.core.cache import Cache
from app.core.enums import BudgetStatus, SpendCategory
from app.repositories.budget_repository import BudgetRepository
from app.schemas.common import to_money, to_pct
from app.schemas.evaluation import (
    CategoryEvaluation,
    EvaluationRequest,
    EvaluationResponse,
)

CACHE_NAMESPACE = "evaluation"


class EvaluationService:
    def __init__(self, repository: BudgetRepository, cache: Cache, ttl_seconds: int) -> None:
        self._repository = repository
        self._cache = cache
        self._ttl_seconds = ttl_seconds

    async def evaluate(self, request: EvaluationRequest) -> EvaluationResponse:
        fingerprint = await self._repository.fingerprint()
        cache_key = self._cache_key(request, fingerprint)

        cached = await self._cache.get(cache_key)
        if cached is not None:
            return EvaluationResponse.model_validate({**cached, "cached": True})

        response = await self._compute(request)
        await self._cache.set(cache_key, response.model_dump(mode="json"), self._ttl_seconds)
        return response

    async def _compute(self, request: EvaluationRequest) -> EvaluationResponse:
        budgets = {budget.category: budget for budget in await self._repository.list_active()}

        spending_by_category: dict[SpendCategory, Decimal] = {}
        for entry in request.spending:
            spending_by_category[entry.category] = (
                spending_by_category.get(entry.category, Decimal("0")) + entry.monthly_amount_brl
            )

        results: list[CategoryEvaluation] = []
        unbudgeted: list[SpendCategory] = []
        total_spent = Decimal("0")
        total_limit = Decimal("0")

        for category, amount in spending_by_category.items():
            total_spent += amount
            budget = budgets.get(category)
            if budget is None:
                unbudgeted.append(category)
                continue

            limit = budget.monthly_limit_brl
            total_limit += limit
            usage_pct = (amount / limit * 100) if limit else Decimal("0")

            results.append(
                CategoryEvaluation(
                    category=category,
                    monthly_amount_brl=to_money(amount),
                    monthly_limit_brl=to_money(limit),
                    alert_threshold_pct=budget.alert_threshold_pct,
                    usage_pct=to_pct(usage_pct),
                    remaining_brl=to_money(limit - amount),
                    status=self._classify(usage_pct, budget.alert_threshold_pct),
                )
            )

        # Categorias com meta ativa e nenhum gasto informado ainda contam no limite total,
        # senão o total consolidado ficaria menor do que o orçamento realmente disponível.
        for category, budget in budgets.items():
            if category not in spending_by_category:
                total_limit += budget.monthly_limit_brl

        results.sort(key=lambda item: item.usage_pct, reverse=True)

        return EvaluationResponse(
            reference_month=request.reference_month or _current_month(),
            evaluated_at=datetime.now(timezone.utc),
            total_monthly_amount_brl=to_money(total_spent),
            total_monthly_limit_brl=to_money(total_limit),
            overall_status=self._overall_status(results),
            results=results,
            unbudgeted_categories=sorted(unbudgeted, key=lambda item: item.value),
            cached=False,
        )

    @staticmethod
    def _classify(usage_pct: Decimal, alert_threshold_pct: int) -> BudgetStatus:
        if usage_pct > 100:
            return BudgetStatus.EXCEEDED
        if usage_pct >= alert_threshold_pct:
            return BudgetStatus.ALERT
        return BudgetStatus.OK

    @staticmethod
    def _overall_status(results: list[CategoryEvaluation]) -> BudgetStatus:
        """The consolidated status is the worst individual status."""
        statuses = {result.status for result in results}
        if BudgetStatus.EXCEEDED in statuses:
            return BudgetStatus.EXCEEDED
        if BudgetStatus.ALERT in statuses:
            return BudgetStatus.ALERT
        return BudgetStatus.OK

    @staticmethod
    def _cache_key(request: EvaluationRequest, fingerprint: str) -> str:
        payload = json.dumps(request.model_dump(mode="json"), sort_keys=True)
        digest = hashlib.sha256(f"{fingerprint}|{payload}".encode()).hexdigest()
        return f"{CACHE_NAMESPACE}:{digest}"


def _current_month() -> str:
    today = datetime.now(timezone.utc).date()
    return f"{today.year:04d}-{today.month:02d}"
