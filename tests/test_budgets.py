"""CRUD, authentication, filtering, sorting and pagination for budgets."""

from tests.conftest import create_budget


async def test_requires_api_key(anonymous_client):
    response = await anonymous_client.get("/api/v1/budgets")

    assert response.status_code == 401
    assert response.json()["type"] == "http-error"


async def test_create_and_read_budget(client):
    created = await create_budget(client, "STREAMING", 120.00)

    assert created["category"] == "STREAMING"
    assert created["monthly_limit_brl"] == 120.0

    response = await client.get(f"/api/v1/budgets/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


async def test_category_accepts_a_single_budget(client):
    await create_budget(client, "SAAS", 300.00)

    response = await client.post(
        "/api/v1/budgets",
        json={"category": "SAAS", "monthly_limit_brl": 90.00},
    )

    assert response.status_code == 409
    assert response.json()["type"] == "duplicate-budget-category"


async def test_replace_budget(client):
    created = await create_budget(client, "GAMING", 80.00)

    response = await client.put(
        f"/api/v1/budgets/{created['id']}",
        json={
            "category": "GAMING",
            "monthly_limit_brl": 150.00,
            "alert_threshold_pct": 60,
            "active": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["monthly_limit_brl"] == 150.0
    assert body["alert_threshold_pct"] == 60
    assert body["active"] is False


async def test_delete_budget(client):
    created = await create_budget(client, "HEALTH", 200.00)

    assert (await client.delete(f"/api/v1/budgets/{created['id']}")).status_code == 204

    missing = await client.get(f"/api/v1/budgets/{created['id']}")
    assert missing.status_code == 404
    assert missing.json()["type"] == "budget-not-found"


async def test_listing_filters_sorts_and_paginates(client):
    await create_budget(client, "STREAMING", 120.00)
    await create_budget(client, "SAAS", 300.00)
    await create_budget(client, "GAMING", 80.00)

    filtered = await client.get("/api/v1/budgets", params={"category": "SAAS"})
    assert filtered.status_code == 200
    assert [item["category"] for item in filtered.json()["items"]] == ["SAAS"]

    ordered = await client.get(
        "/api/v1/budgets", params={"sort_by": "monthly_limit_brl", "order": "desc"}
    )
    assert [item["monthly_limit_brl"] for item in ordered.json()["items"]] == [300.0, 120.0, 80.0]

    paginated = await client.get("/api/v1/budgets", params={"page": 2, "page_size": 2})
    body = paginated.json()
    assert len(body["items"]) == 1
    assert body["meta"] == {"page": 2, "page_size": 2, "total_items": 3, "total_pages": 2}


async def test_rejects_invalid_payload(client):
    response = await client.post(
        "/api/v1/budgets",
        json={"category": "STREAMING", "monthly_limit_brl": -10},
    )

    assert response.status_code == 422
    assert response.json()["type"] == "validation-error"
