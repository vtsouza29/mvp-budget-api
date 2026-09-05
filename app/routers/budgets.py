"""CRUD routes for the Budget aggregate."""

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.enums import SpendCategory
from app.dependencies import get_budget_service
from app.repositories.budget_repository import SORTABLE_FIELDS
from app.schemas.budget import BudgetCreate, BudgetResponse, BudgetUpdate
from app.schemas.common import Page, PageMeta
from app.security import require_api_key
from app.services.budget_service import BudgetService

router = APIRouter(
    prefix="/api/v1/budgets",
    tags=["Metas"],
    dependencies=[Depends(require_api_key)],
)


@router.post(
    "",
    response_model=BudgetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma meta de gasto",
    description="Cadastra o limite mensal de uma categoria. Cada categoria admite uma única meta.",
)
async def create_budget(
    payload: BudgetCreate,
    service: BudgetService = Depends(get_budget_service),
) -> BudgetResponse:
    budget = await service.create(payload)
    return BudgetResponse.model_validate(budget)


@router.get(
    "",
    response_model=Page[BudgetResponse],
    summary="Lista metas com filtro, ordenação e paginação",
    description="Permite filtrar por categoria e por situação, ordenar por diferentes campos e paginar o resultado.",
)
async def list_budgets(
    category: SpendCategory | None = Query(default=None, description="Filtra por categoria."),
    active: bool | None = Query(default=None, description="Filtra por metas ativas ou inativas."),
    sort_by: str = Query(default="category", description=f"Campo de ordenação: {', '.join(SORTABLE_FIELDS)}."),
    order: str = Query(default="asc", pattern="^(asc|desc)$", description="Sentido da ordenação."),
    page: int = Query(default=1, ge=1, description="Página desejada."),
    page_size: int = Query(default=20, ge=1, le=100, description="Itens por página."),
    service: BudgetService = Depends(get_budget_service),
) -> Page[BudgetResponse]:
    budgets, total = await service.list_paginated(
        category=category,
        active=active,
        sort_by=sort_by,
        order=order,
        page=page,
        page_size=page_size,
    )
    total_pages = (total + page_size - 1) // page_size
    return Page[BudgetResponse](
        items=[BudgetResponse.model_validate(budget) for budget in budgets],
        meta=PageMeta(
            page=page, page_size=page_size, total_items=total, total_pages=total_pages
        ),
    )


@router.get(
    "/{budget_id}",
    response_model=BudgetResponse,
    summary="Consulta uma meta pelo identificador",
)
async def get_budget(
    budget_id: str,
    service: BudgetService = Depends(get_budget_service),
) -> BudgetResponse:
    budget = await service.get(budget_id)
    return BudgetResponse.model_validate(budget)


@router.put(
    "/{budget_id}",
    response_model=BudgetResponse,
    summary="Substitui uma meta existente",
    description="Substitui integralmente os dados da meta, conforme a semântica do método PUT.",
)
async def replace_budget(
    budget_id: str,
    payload: BudgetUpdate,
    service: BudgetService = Depends(get_budget_service),
) -> BudgetResponse:
    budget = await service.replace(budget_id, payload)
    return BudgetResponse.model_validate(budget)


@router.delete(
    "/{budget_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove uma meta",
)
async def delete_budget(
    budget_id: str,
    service: BudgetService = Depends(get_budget_service),
) -> Response:
    await service.delete(budget_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
