"""Data access for the Budget aggregate.

Keeping SQLAlchemy behind this boundary means the services read as business
rules, and the routers never touch a query.
"""

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SpendCategory
from app.models.budget import Budget

SORTABLE_FIELDS = ("category", "monthly_limit_brl", "created_at", "updated_at")


class BudgetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, budget_id: str) -> Budget | None:
        return await self._session.get(Budget, budget_id)

    async def get_by_category(self, category: SpendCategory) -> Budget | None:
        result = await self._session.execute(
            select(Budget).where(Budget.category == category)
        )
        return result.scalar_one_or_none()

    async def list_active(self) -> Sequence[Budget]:
        result = await self._session.execute(
            select(Budget).where(Budget.active.is_(True))
        )
        return result.scalars().all()

    async def list_paginated(
        self,
        *,
        category: SpendCategory | None = None,
        active: bool | None = None,
        sort_by: str = "category",
        order: str = "asc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[Sequence[Budget], int]:
        """Return one page of budgets plus the total number of matches."""
        filters = []
        if category is not None:
            filters.append(Budget.category == category)
        if active is not None:
            filters.append(Budget.active.is_(active))

        total = await self._session.scalar(
            select(func.count()).select_from(Budget).where(*filters)
        )

        column = getattr(Budget, sort_by if sort_by in SORTABLE_FIELDS else "category")
        ordering = column.desc() if order == "desc" else column.asc()

        result = await self._session.execute(
            select(Budget)
            .where(*filters)
            .order_by(ordering)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return result.scalars().all(), int(total or 0)

    async def add(self, budget: Budget) -> Budget:
        self._session.add(budget)
        await self._session.commit()
        await self._session.refresh(budget)
        return budget

    async def save(self, budget: Budget) -> Budget:
        await self._session.commit()
        await self._session.refresh(budget)
        return budget

    async def delete(self, budget: Budget) -> None:
        await self._session.delete(budget)
        await self._session.commit()

    async def fingerprint(self) -> str:
        """Cheap signature of the current budget set.

        Included in evaluation cache keys so that changing a budget invalidates
        every evaluation computed against the previous configuration.
        """
        result = await self._session.execute(
            select(func.count(Budget.id), func.max(Budget.updated_at))
        )
        count, last_update = result.one()
        return f"{count}:{last_update.isoformat() if last_update else 'never'}"
