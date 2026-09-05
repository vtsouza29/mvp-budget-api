"""Charge distribution across the projection window."""

BASE_URL = "/api/v1/projections"


async def test_monthly_subscription_is_charged_every_month(client):
    response = await client.post(
        BASE_URL,
        json={
            "months": 3,
            "start_month": "2026-09",
            "subscriptions": [
                {
                    "name": "Streaming Plus",
                    "category": "STREAMING",
                    "amount_brl": 50.00,
                    "billing_cycle": "MONTHLY",
                    "next_renewal_on": "2026-09-10",
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert [month["total_brl"] for month in body["timeline"]] == [50.0, 50.0, 50.0]
    assert body["total_brl"] == 150.0
    assert body["monthly_average_brl"] == 50.0


async def test_quarterly_subscription_skips_two_months(client):
    response = await client.post(
        BASE_URL,
        json={
            "months": 6,
            "start_month": "2026-09",
            "subscriptions": [
                {
                    "name": "Cloud Backup",
                    "category": "SAAS",
                    "amount_brl": 90.00,
                    "billing_cycle": "QUARTERLY",
                    "next_renewal_on": "2026-10-05",
                }
            ],
        },
    )

    months = {month["month"]: month["total_brl"] for month in response.json()["timeline"]}
    assert months == {
        "2026-09": 0.0,
        "2026-10": 90.0,
        "2026-11": 0.0,
        "2026-12": 0.0,
        "2027-01": 90.0,
        "2027-02": 0.0,
    }


async def test_past_renewal_date_rolls_forward_to_the_window(client):
    """A yearly plan renewed last March must still land on March of the window."""
    response = await client.post(
        BASE_URL,
        json={
            "months": 12,
            "start_month": "2026-09",
            "subscriptions": [
                {
                    "name": "Annual Course",
                    "category": "EDUCATION",
                    "amount_brl": 1200.00,
                    "billing_cycle": "YEARLY",
                    "next_renewal_on": "2026-03-15",
                }
            ],
        },
    )

    body = response.json()
    charged = [month["month"] for month in body["timeline"] if month["total_brl"] > 0]
    assert charged == ["2027-03"]
    assert body["heaviest_month"] == "2027-03"
    assert body["total_brl"] == 1200.0


async def test_totals_are_grouped_by_category(client):
    response = await client.post(
        BASE_URL,
        json={
            "months": 2,
            "start_month": "2026-09",
            "subscriptions": [
                {
                    "name": "Streaming Plus",
                    "category": "STREAMING",
                    "amount_brl": 40.00,
                    "billing_cycle": "MONTHLY",
                    "next_renewal_on": "2026-09-01",
                },
                {
                    "name": "Gym App",
                    "category": "HEALTH",
                    "amount_brl": 30.00,
                    "billing_cycle": "MONTHLY",
                    "next_renewal_on": "2026-09-01",
                },
            ],
        },
    )

    body = response.json()
    assert body["by_category"] == {"HEALTH": 60.0, "STREAMING": 80.0}
    assert body["timeline"][0]["by_category"] == {"HEALTH": 30.0, "STREAMING": 40.0}


async def test_identical_request_is_served_from_cache(client):
    payload = {
        "months": 12,
        "start_month": "2026-09",
        "subscriptions": [
            {
                "name": "Streaming Plus",
                "category": "STREAMING",
                "amount_brl": 50.00,
                "billing_cycle": "MONTHLY",
                "next_renewal_on": "2026-09-10",
            }
        ],
    }

    first = await client.post(BASE_URL, json=payload)
    second = await client.post(BASE_URL, json=payload)

    assert first.json()["cached"] is False
    assert second.json()["cached"] is True
