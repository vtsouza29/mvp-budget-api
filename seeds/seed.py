"""Idempotent synthetic data, so a fresh container is demo-ready."""

import asyncio
from decimal import Decimal

from app.core.enums import SpendCategory
from app.database import SessionFactory, init_database
from app.models.budget import Budget
from app.repositories.budget_repository import BudgetRepository

DEFAULT_BUDGETS = [
    (SpendCategory.STREAMING, Decimal("120.00"), 80),
    (SpendCategory.SAAS, Decimal("300.00"), 75),
    (SpendCategory.GAMING, Decimal("80.00"), 90),
    (SpendCategory.EDUCATION, Decimal("250.00"), 85),
    (SpendCategory.HEALTH, Decimal("200.00"), 80),
]


async def seed_budgets() -> int:
    """Create the default budgets that are still missing. Safe to run repeatedly."""
    created = 0
    async with SessionFactory() as session:
        repository = BudgetRepository(session)
        for category, limit, threshold in DEFAULT_BUDGETS:
            if await repository.get_by_category(category) is not None:
                continue
            await repository.add(
                Budget(
                    category=category,
                    monthly_limit_brl=limit,
                    alert_threshold_pct=threshold,
                    active=True,
                )
            )
            created += 1
    return created


async def _main() -> None:
    await init_database()
    created = await seed_budgets()
    print(f"{created} meta(s) criada(s).")


if __name__ == "__main__":
    asyncio.run(_main())
