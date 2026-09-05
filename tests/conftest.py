"""Test wiring: an isolated SQLite file, an in-process cache, no Redis."""

import os
import tempfile
from pathlib import Path

_TEMP_DIR = Path(tempfile.mkdtemp(prefix="budget-api-tests-"))

# Configurado antes de importar a aplicação, que lê as settings no import.
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEMP_DIR / 'test.db'}"
os.environ["API_KEY"] = "test-key"
os.environ["REDIS_URL"] = ""
os.environ["SEED_ON_STARTUP"] = "false"

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import delete  # noqa: E402

from app.core.cache import InMemoryTTLCache  # noqa: E402
from app.database import SessionFactory, init_database  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models.budget import Budget  # noqa: E402

API_KEY = "test-key"


@pytest.fixture(autouse=True)
async def clean_database():
    """Every test starts from an empty budgets table."""
    await init_database()
    async with SessionFactory() as session:
        await session.execute(delete(Budget))
        await session.commit()
    yield


@pytest.fixture
def app_instance():
    app = create_app()
    # O lifespan não roda sob ASGITransport, então o cache é injetado aqui.
    app.state.cache = InMemoryTTLCache()
    return app


@pytest.fixture
async def client(app_instance):
    transport = ASGITransport(app=app_instance)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={"X-API-Key": API_KEY},
    ) as http_client:
        yield http_client


@pytest.fixture
async def anonymous_client(app_instance):
    transport = ASGITransport(app=app_instance)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client


async def create_budget(client: AsyncClient, category: str, limit: float, threshold: int = 80) -> dict:
    """Helper used by the tests to arrange budgets."""
    response = await client.post(
        "/api/v1/budgets",
        json={
            "category": category,
            "monthly_limit_brl": limit,
            "alert_threshold_pct": threshold,
            "active": True,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()
