"""Health endpoint is open and reports each dependency."""


async def test_health_is_public_and_reports_dependencies(anonymous_client):
    response = await anonymous_client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "mvp-budget-api"

    reported = {dependency["name"]: dependency["status"] for dependency in body["dependencies"]}
    assert reported["database"] == "up"
    # Sem Redis nos testes, o cache em memória é reportado como degradado.
    assert reported["cache"] == "degraded"
    assert body["status"] == "degraded"
