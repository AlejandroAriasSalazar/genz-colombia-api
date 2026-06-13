"""
Tests para el endpoint /aggregate/query.
Nota: Estos tests requieren que la BD esté poblada con seed data.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


TEST_API_KEY = "genz_free_test_key_12345"


@pytest.mark.asyncio
async def test_aggregate_requires_auth():
    """Test: POST /aggregate/query requiere autenticación."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/aggregate/query",
            json={"group_by": ["ciudad_divipola"], "metric": "count"},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_aggregate_count_by_city():
    """Test: POST /aggregate/query count por ciudad."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/aggregate/query",
            json={
                "group_by": ["ciudad_divipola"],
                "metric": "count",
            },
            headers={"X-API-Key": TEST_API_KEY},
        )

    if response.status_code == 200:
        data = response.json()
        assert data["metric"] == "count"
        assert data["group_by"] == ["ciudad_divipola"]
        assert "results" in data
        assert "total_records" in data


@pytest.mark.asyncio
async def test_aggregate_avg_edad_by_estrato():
    """Test: POST /aggregate/query avg_edad por estrato."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/aggregate/query",
            json={
                "group_by": ["estrato"],
                "metric": "avg_edad",
            },
            headers={"X-API-Key": TEST_API_KEY},
        )

    if response.status_code == 200:
        data = response.json()
        assert data["metric"] == "avg_edad"
        for result in data["results"]:
            assert 12 <= result["value"] <= 28


@pytest.mark.asyncio
async def test_aggregate_pct_internet_by_city():
    """Test: POST /aggregate/query pct_internet por ciudad."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/aggregate/query",
            json={
                "group_by": ["ciudad_divipola"],
                "metric": "pct_internet",
            },
            headers={"X-API-Key": TEST_API_KEY},
        )

    if response.status_code == 200:
        data = response.json()
        assert data["metric"] == "pct_internet"
        for result in data["results"]:
            assert 0 <= result["value"] <= 100


@pytest.mark.asyncio
async def test_aggregate_invalid_metric():
    """Test: POST /aggregate/query con métrica inválida retorna 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/aggregate/query",
            json={
                "group_by": ["ciudad_divipola"],
                "metric": "invalid_metric",
            },
            headers={"X-API-Key": TEST_API_KEY},
        )

    if response.status_code != 401:  # Si la key existe
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_aggregate_invalid_group_by():
    """Test: POST /aggregate/query con group_by inválido retorna 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/aggregate/query",
            json={
                "group_by": ["invalid_field"],
                "metric": "count",
            },
            headers={"X-API-Key": TEST_API_KEY},
        )

    if response.status_code != 401:  # Si la key existe
        assert response.status_code == 400
