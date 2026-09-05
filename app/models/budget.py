"""The Budget aggregate: a monthly spending limit for one category."""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import SpendCategory
from app.core.types import MoneyType
from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Budget(Base):
    """A category may hold at most one budget, which is what makes it a key."""

    __tablename__ = "budgets"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    category: Mapped[SpendCategory] = mapped_column(
        SAEnum(SpendCategory, native_enum=False, length=20),
        unique=True,
        index=True,
        nullable=False,
    )
    monthly_limit_brl: Mapped[Decimal] = mapped_column(MoneyType, nullable=False)
    alert_threshold_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=80)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    def __repr__(self) -> str:  # pragma: no cover - conveniência de debug
        return f"<Budget {self.category.value} limit={self.monthly_limit_brl}>"
