"""Spending evaluated against the stored budgets."""

from tests.conftest import create_budget


async def test_classifies_each_category(client):
    await create_budget(client, "STREAMING", 100.00, threshold=80)
    await create_budget(client, "SAAS", 100.00, threshold=80)
    await create_budget(client, "GAMING", 100.00, threshold=80)

    response = await client.post(
        "/api/v1/evaluations",
        json={
            "reference_month": "2026-09",
            "spending": [
                {"category": "STREAMING", "monthly_amount_brl": 50.00},
                {"category": "SAAS", "monthly_amount_brl": 85.00},
                {"category": "GAMING", "monthly_amount_brl": 130.00},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    status_by_category = {item["category"]: item["status"] for item in body["results"]}

    assert status_by_category == {"STREAMING": "OK", "SAAS": "ALERT", "GAMING": "EXCEEDED"}
    assert body["overall_status"] == "EXCEEDED"
    assert body["total_monthly_amount_brl"] == 265.0
    assert body["total_monthly_limit_brl"] == 300.0


async def test_reports_remaining_amount_and_usage(client):
    await create_budget(client, "HEALTH", 200.00)

    response = await client.post(
        "/api/v1/evaluations",
        json={"spending": [{"category": "HEALTH", "monthly_amount_brl": 250.00}]},
    )

    result = response.json()["results"][0]
    assert result["usage_pct"] == 125.0
    assert result["remaining_brl"] == -50.0


async def test_flags_categories_without_a_budget(client):
    await create_budget(client, "STREAMING", 100.00)

    response = await client.post(
        "/api/v1/evaluations",
        json={
            "spending": [
                {"category": "STREAMING", "monthly_amount_brl": 10.00},
                {"category": "OTHER", "monthly_amount_brl": 40.00},
            ]
        },
    )

    body = response.json()
    assert body["unbudgeted_categories"] == ["OTHER"]
    assert [item["category"] for item in body["results"]] == ["STREAMING"]


async def test_inactive_budgets_are_ignored(client):
    created = await create_budget(client, "GAMING", 80.00)
    await client.put(
        f"/api/v1/budgets/{created['id']}",
        json={"category": "GAMING", "monthly_limit_brl": 80.00, "active": False},
    )

    response = await client.post(
        "/api/v1/evaluations",
        json={"spending": [{"category": "GAMING", "monthly_amount_brl": 500.00}]},
    )

    assert response.json()["unbudgeted_categories"] == ["GAMING"]


async def test_second_identical_call_is_served_from_cache(client):
    await create_budget(client, "SAAS", 300.00)
    payload = {
        "reference_month": "2026-09",
        "spending": [{"category": "SAAS", "monthly_amount_brl": 120.00}],
    }

    first = await client.post("/api/v1/evaluations", json=payload)
    second = await client.post("/api/v1/evaluations", json=payload)

    assert first.json()["cached"] is False
    assert second.json()["cached"] is True


async def test_changing_a_budget_invalidates_the_cache(client):
    created = await create_budget(client, "SAAS", 300.00)
    payload = {
        "reference_month": "2026-09",
        "spending": [{"category": "SAAS", "monthly_amount_brl": 280.00}],
    }

    first = await client.post("/api/v1/evaluations", json=payload)
    assert first.json()["results"][0]["status"] == "ALERT"

    await client.put(
        f"/api/v1/budgets/{created['id']}",
        json={"category": "SAAS", "monthly_limit_brl": 1000.00, "active": True},
    )

    second = await client.post("/api/v1/evaluations", json=payload)
    assert second.json()["cached"] is False
    assert second.json()["results"][0]["status"] == "OK"
