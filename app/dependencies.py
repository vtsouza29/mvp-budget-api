"""Dependency wiring: routers ask for services, never for sessions or caches."""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.cache import Cache
from app.database import get_session
from app.repositories.budget_repository import BudgetRepository
from app.services.budget_service import BudgetService
from app.services.evaluation_service import EvaluationService
from app.services.projection_service import ProjectionService


def get_cache(request: Request) -> Cache:
    """The cache backend chosen at startup, shared by the whole application."""
    return request.app.state.cache


def get_budget_repository(session: AsyncSession = Depends(get_session)) -> BudgetRepository:
    return BudgetRepository(session)


def get_budget_service(
    repository: BudgetRepository = Depends(get_budget_repository),
) -> BudgetService:
    return BudgetService(repository)


def get_evaluation_service(
    repository: BudgetRepository = Depends(get_budget_repository),
    cache: Cache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
) -> EvaluationService:
    return EvaluationService(repository, cache, settings.cache_ttl_seconds)


def get_projection_service(
    cache: Cache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
) -> ProjectionService:
    return ProjectionService(cache, settings.cache_ttl_seconds)
