def test_health_and_readiness(client):
    live = client.get("/api/v2/health/live")
    assert live.status_code == 200
    assert live.json()["version"] == "2.0.0"

    ready = client.get("/api/v2/health/ready")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"
    assert ready.json()["checks"]["published_dataset"] is True


def test_bootstrap_status_is_protected(client):
    hidden = client.get("/api/v2/health/bootstrap")
    assert hidden.status_code == 404

    visible = client.get(
        "/api/v2/health/bootstrap",
        headers={"X-Operations-Key": "test-operations-key"},
    )
    assert visible.status_code == 200
    assert visible.json() == {"status": "pending", "phase": "not_started"}


def test_public_catalog_is_traceable(client):
    metadata = client.get("/api/v2/metadata")
    assert metadata.status_code == 200
    assert "music_interest" in metadata.json()["excluded_unvalidated_variables"]

    sources = client.get("/api/v2/sources")
    assert sources.status_code == 200
    assert sources.json()["sources"][0]["owner"] == "DANE"

    versions = client.get("/api/v2/versions")
    assert versions.status_code == 200
    assert versions.json()["versions"][0]["status"] == "published"

    quality = client.get("/api/v2/quality/test-2026-m1")
    assert quality.status_code == 200
    assert quality.json()["quality_report"]["status"] == "passed"


def test_openapi_declares_api_key_security(client):
    schema = client.get("/openapi.json").json()
    schemes = schema["components"]["securitySchemes"]
    assert schemes["APIKeyHeader"]["name"] == "X-API-Key"
    operation = schema["paths"]["/api/v2/population/sample"]["post"]
    assert {"APIKeyHeader": ["sample:read"]} in operation["security"]


def test_protected_endpoint_requires_auth(client):
    response = client.post("/api/v2/population/sample", json={"sample_size": 2})
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")


def test_sample_is_reproducible_and_filtered(client, auth_headers):
    payload = {
        "filters": {"municipality_code": "11001", "year": 2026, "age_min": 18, "age_max": 24},
        "sample_size": 20,
        "seed": 123,
    }
    first = client.post("/api/v2/population/sample", json=payload, headers=auth_headers)
    second = client.post("/api/v2/population/sample", json=payload, headers=auth_headers)
    assert first.status_code == second.status_code == 200
    assert first.json()["persons"] == second.json()["persons"]
    assert len(first.json()["persons"]) == 20
    assert all(person["municipality_code"] == "11001" for person in first.json()["persons"])
    assert all(18 <= person["age"] <= 24 for person in first.json()["persons"])
    assert first.headers["X-RateLimit-Minute-Remaining"].isdigit()


def test_sample_enforces_tier_limit(client, auth_headers):
    response = client.post(
        "/api/v2/population/sample",
        json={"sample_size": 101},
        headers=auth_headers,
    )
    assert response.status_code == 403


def test_aggregate_uses_nested_filters(client, auth_headers):
    response = client.post(
        "/api/v2/aggregate/query",
        json={
            "group_by": ["sex"],
            "metric": "population",
            "filters": {
                "municipality_code": "05001",
                "year": 2026,
                "age_min": 18,
                "age_max": 18,
            },
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filters_applied"]["municipality_code"] == "05001"
    assert {item["group"]["sex"] for item in data["results"]} == {"M", "F"}
    assert data["total_population"] == (10 + 18) + (10 + 18 + 5)


def test_invalid_age_range_is_rejected(client, auth_headers):
    response = client.post(
        "/api/v2/aggregate/query",
        json={"group_by": ["age"], "filters": {"age_min": 30, "age_max": 20}},
        headers=auth_headers,
    )
    assert response.status_code == 422
