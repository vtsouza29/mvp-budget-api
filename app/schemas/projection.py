"""Schemas for the twelve-month spending projection."""

from datetime import date

from pydantic import BaseModel, Field

from app.core.enums import BillingCycle, SpendCategory
from app.schemas.common import MoneyIn
from app.schemas.evaluation import MONTH_PATTERN


class ProjectionSubscription(BaseModel):
    """One recurring charge, already converted to BRL by the caller."""

    name: str = Field(min_length=1, max_length=120)
    category: SpendCategory
    amount_brl: MoneyIn = Field(description="Valor de cada cobrança, em reais.")
    billing_cycle: BillingCycle
    next_renewal_on: date = Field(description="Data da próxima cobrança.")


class ProjectionRequest(BaseModel):
    """Set of subscriptions to project forward."""

    months: int = Field(default=12, ge=1, le=36, description="Tamanho da janela de projeção.")
    start_month: str | None = Field(
        default=None,
        pattern=MONTH_PATTERN,
        description="Primeiro mês da janela, no formato AAAA-MM. Padrão: mês corrente.",
        examples=["2026-09"],
    )
    subscriptions: list[ProjectionSubscription] = Field(min_length=1)


class ProjectedCharge(BaseModel):
    """A single charge landing in a given month."""

    name: str
    category: SpendCategory
    amount_brl: float


class MonthlyProjection(BaseModel):
    """Everything that falls due in one month of the window."""

    month: str = Field(description="Mês no formato AAAA-MM.")
    total_brl: float
    by_category: dict[SpendCategory, float]
    charges: list[ProjectedCharge]


class ProjectionResponse(BaseModel):
    """Projection over the whole window."""

    start_month: str
    months: int
    total_brl: float
    monthly_average_brl: float
    heaviest_month: str = Field(description="Mês de maior desembolso na janela.")
    by_category: dict[SpendCategory, float]
    timeline: list[MonthlyProjection]
    cached: bool = Field(default=False, description="Indica se a resposta veio do cache.")
