"""Business rules for creating, listing and changing budgets."""

from collections.abc import Sequence

from fastapi import status

from app.core.enums import SpendCategory
from app.core.errors import DomainError
from app.models.budget import Budget
from app.repositories.budget_repository import BudgetRepository
from app.schemas.budget import BudgetCreate, BudgetUpdate


class BudgetService:
    def __init__(self, repository: BudgetRepository) -> None:
        self._repository = repository

    async def create(self, payload: BudgetCreate) -> Budget:
        await self._reject_duplicate_category(payload.category)
        budget = Budget(
            category=payload.category,
            monthly_limit_brl=payload.monthly_limit_brl,
            alert_threshold_pct=payload.alert_threshold_pct,
            active=payload.active,
        )
        return await self._repository.add(budget)

    async def get(self, budget_id: str) -> Budget:
        budget = await self._repository.get_by_id(budget_id)
        if budget is None:
            raise DomainError(
                f"Nenhuma meta encontrada com o id {budget_id}.",
                status_code=status.HTTP_404_NOT_FOUND,
                error_type="budget-not-found",
            )
        return budget

    async def list_paginated(self, **criteria) -> tuple[Sequence[Budget], int]:
        return await self._repository.list_paginated(**criteria)

    async def replace(self, budget_id: str, payload: BudgetUpdate) -> Budget:
        budget = await self.get(budget_id)
        if payload.category != budget.category:
            await self._reject_duplicate_category(payload.category)

        budget.category = payload.category
        budget.monthly_limit_brl = payload.monthly_limit_brl
        budget.alert_threshold_pct = payload.alert_threshold_pct
        budget.active = payload.active
        return await self._repository.save(budget)

    async def delete(self, budget_id: str) -> None:
        budget = await self.get(budget_id)
        await self._repository.delete(budget)

    async def _reject_duplicate_category(self, category: SpendCategory) -> None:
        if await self._repository.get_by_category(category) is not None:
            raise DomainError(
                f"Já existe uma meta cadastrada para a categoria {category.value}.",
                status_code=status.HTTP_409_CONFLICT,
                error_type="duplicate-budget-category",
            )
