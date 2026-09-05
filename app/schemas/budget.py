"""Request and response schemas for the Budget aggregate."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.core.enums import SpendCategory
from app.schemas.common import MoneyIn, to_money

_THRESHOLD = Field(
    default=80,
    ge=1,
    le=100,
    description="Percentual do limite a partir do qual a categoria entra em alerta.",
)


class BudgetCreate(BaseModel):
    """Payload to create a budget for a category."""

    category: SpendCategory = Field(description="Categoria de gasto controlada por esta meta.")
    monthly_limit_brl: MoneyIn = Field(description="Limite mensal em reais.")
    alert_threshold_pct: int = _THRESHOLD
    active: bool = Field(default=True, description="Se a meta deve ser considerada nas avaliações.")


class BudgetUpdate(BaseModel):
    """Full replacement payload, matching PUT semantics."""

    category: SpendCategory = Field(description="Categoria de gasto controlada por esta meta.")
    monthly_limit_brl: MoneyIn = Field(description="Limite mensal em reais.")
    alert_threshold_pct: int = _THRESHOLD
    active: bool = Field(default=True, description="Se a meta deve ser considerada nas avaliações.")


class BudgetResponse(BaseModel):
    """Budget as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    category: SpendCategory
    monthly_limit_brl: float
    alert_threshold_pct: int
    active: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer("monthly_limit_brl")
    def _serialize_limit(self, value: float) -> float:
        return to_money(value)
