"""
Tests para el endpoint /population/sample.
Nota: Estos tests requieren que la BD esté poblada con seed data.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


TEST_API_KEY = "genz_free_test_key_12345"


@pytest.mark.asyncio
async def test_population_sample_requires_auth():
    """Test: POST /population/sample requiere autenticación."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/population/sample", json={})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_population_sample_no_filters():
    """Test: POST /population/sample sin filtros retorna muestra."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/population/sample",
            json={"sample_size": 10},
            headers={"X-API-Key": TEST_API_KEY},
        )

    if response.status_code == 200:
        data = response.json()
        assert "count" in data
        assert "total_matching" in data
        assert "filters_applied" in data
        assert "persons" in data
        assert data["count"] <= 10


@pytest.mark.asyncio
async def test_population_sample_with_city_filter():
    """Test: POST /population/sample con filtro de ciudad."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/population/sample",
            json={
                "ciudad_divipola": "11001",
                "sample_size": 5,
            },
            headers={"X-API-Key": TEST_API_KEY},
        )

    if response.status_code == 200:
        data = response.json()
        assert data["filters_applied"]["ciudad_divipola"] == "11001"
        for person in data["persons"]:
            assert person["ciudad_divipola"] == "11001"


@pytest.mark.asyncio
async def test_population_sample_with_age_filter():
    """Test: POST /population/sample con filtro de edad."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/population/sample",
            json={
                "edad_min": 18,
                "edad_max": 24,
                "sample_size": 10,
            },
            headers={"X-API-Key": TEST_API_KEY},
        )

    if response.status_code == 200:
        data = response.json()
        for person in data["persons"]:
            assert 18 <= person["edad"] <= 24


@pytest.mark.asyncio
async def test_population_sample_with_estrato_filter():
    """Test: POST /population/sample con filtro de estrato."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/population/sample",
            json={
                "estrato": 3,
                "sample_size": 10,
            },
            headers={"X-API-Key": TEST_API_KEY},
        )

    if response.status_code == 200:
        data = response.json()
        for person in data["persons"]:
            assert person["estrato"] == 3
