"""Vocabulary shared between the budget service and its consumers.

Both services in this MVP must agree on these values, so they are defined once
here and mirrored on the subscription side.
"""

from enum import Enum


class SpendCategory(str, Enum):
    """Category a recurring expense belongs to."""

    STREAMING = "STREAMING"
    SAAS = "SAAS"
    GAMING = "GAMING"
    EDUCATION = "EDUCATION"
    HEALTH = "HEALTH"
    OTHER = "OTHER"


class BillingCycle(str, Enum):
    """How often a subscription is charged."""

    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"

    @property
    def month_step(self) -> int:
        """Number of months between two consecutive charges."""
        return {"MONTHLY": 1, "QUARTERLY": 3, "YEARLY": 12}[self.value]


class BudgetStatus(str, Enum):
    """Outcome of comparing spending against a budget limit."""

    OK = "OK"
    ALERT = "ALERT"
    EXCEEDED = "EXCEEDED"
