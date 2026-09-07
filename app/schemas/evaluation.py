"""Schemas for evaluating observed spending against the stored budgets."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import BudgetStatus, SpendCategory
from app.schemas.common import MoneyInOrZero

MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


class CategorySpending(BaseModel):
    """Amount already normalised to BRL by the caller, for one category."""

    category: SpendCategory
    monthly_amount_brl: MoneyInOrZero = Field(description="Gasto mensal em reais.")


class EvaluationRequest(BaseModel):
    """Spending snapshot sent by the subscription service."""

    # Os valores reproduzem o gasto das assinaturas sintéticas do seed, para que
    # a chamada isolada no Swagger devolva o mesmo resultado da orquestração real.
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "reference_month": "2026-09",
                "spending": [
                    {"category": "STREAMING", "monthly_amount_brl": 77.80},
                    {"category": "SAAS", "monthly_amount_brl": 173.72},
                    {"category": "GAMING", "monthly_amount_brl": 49.90},
                    {"category": "EDUCATION", "monthly_amount_brl": 123.27},
                    {"category": "HEALTH", "monthly_amount_brl": 39.90},
                ],
            }
        }
    )

    reference_month: str | None = Field(
        default=None,
        pattern=MONTH_PATTERN,
        description="Mês de referência no formato AAAA-MM. Padrão: mês corrente.",
        examples=["2026-09"],
    )
    spending: list[CategorySpending] = Field(
        min_length=1, description="Gasto mensal consolidado por categoria."
    )


class CategoryEvaluation(BaseModel):
    """Outcome for a single category."""

    category: SpendCategory
    monthly_amount_brl: float
    monthly_limit_brl: float
    alert_threshold_pct: int
    usage_pct: float = Field(description="Percentual do limite já consumido.")
    remaining_brl: float = Field(description="Folga restante; negativo quando estourado.")
    status: BudgetStatus


class EvaluationResponse(BaseModel):
    """Consolidated evaluation returned to the caller."""

    reference_month: str
    evaluated_at: datetime
    total_monthly_amount_brl: float
    total_monthly_limit_brl: float
    overall_status: BudgetStatus
    results: list[CategoryEvaluation]
    unbudgeted_categories: list[SpendCategory] = Field(
        description="Categorias com gasto informado, porém sem meta ativa cadastrada."
    )
    cached: bool = Field(default=False, description="Indica se a resposta veio do cache.")
