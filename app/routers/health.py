"""Liveness endpoint reporting the real state of each dependency."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_session
from app.schemas.common import DependencyHealth, HealthResponse

router = APIRouter(tags=["Operação"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Verifica a saúde do serviço e de suas dependências",
    description="Rota aberta, sem autenticação, para uso do Docker e de quem estiver operando o serviço.",
)
async def health(
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    dependencies = [await _check_database(session), _check_cache(request)]
    degraded = any(dependency.status != "up" for dependency in dependencies)

    return HealthResponse(
        status="degraded" if degraded else "healthy",
        service=settings.app_name,
        version=settings.app_version,
        dependencies=dependencies,
    )


async def _check_database(session: AsyncSession) -> DependencyHealth:
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - health nunca deve levantar
        return DependencyHealth(name="database", status="down", detail=str(exc))
    return DependencyHealth(name="database", status="up", detail="sqlite")


def _check_cache(request: Request) -> DependencyHealth:
    cache = request.app.state.cache
    # Um cache em memória funciona, mas não é compartilhado entre réplicas:
    # reportamos "degraded" para que isso não passe despercebido em produção.
    if cache.backend == "redis":
        return DependencyHealth(name="cache", status="up", detail="redis")
    return DependencyHealth(
        name="cache",
        status="degraded",
        detail="cache em memória (Redis indisponível ou não configurado)",
    )
