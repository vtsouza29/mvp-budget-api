"""Application entry point for the budget service."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.core.cache import build_cache
from app.core.correlation import CorrelationIdMiddleware
from app.core.docs import register_documentation_routes
from app.core.errors import register_exception_handlers
from app.database import engine, init_database
from app.routers import budgets, evaluations, health, projections

DESCRIPTION = """
Serviço responsável pelas **metas de gasto** do MVP de controle de assinaturas.

É a componente secundária da arquitetura: guarda o agregado `Budget` em banco próprio,
avalia o gasto informado pela API principal contra as metas cadastradas e projeta o
desembolso dos próximos meses.

Todas as rotas de negócio exigem o cabeçalho `X-API-Key`. A rota `/health` é aberta.
"""


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    _configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)

    await init_database()
    app.state.cache = await build_cache(settings.redis_url)
    logger.info("cache ativo: %s", app.state.cache.backend)

    if settings.seed_on_startup:
        from seeds.seed import seed_budgets

        created = await seed_budgets()
        logger.info("seed concluído, %s metas garantidas", created)

    yield

    await app.state.cache.close()
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="MVP Budget API",
        description=DESCRIPTION,
        version=settings.app_version,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        contact={"name": "MVP - Arquitetura de Software (PUC-Rio)"},
        license_info={"name": "MIT"},
    )

    register_documentation_routes(app)
    app.add_middleware(CorrelationIdMiddleware)
    register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(budgets.router)
    app.include_router(evaluations.router)
    app.include_router(projections.router)

    return app


app = create_app()
