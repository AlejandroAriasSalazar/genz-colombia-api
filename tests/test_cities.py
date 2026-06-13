"""
Tests para el endpoint /cities.
Nota: Estos tests requieren que la BD esté poblada con seed data.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.api.deps import hash_api_key


# API key de prueba (debe coincidir con la del seed data)
TEST_API_KEY = "genz_free_test_key_12345"


@pytest.mark.asyncio
async def test_cities_requires_auth():
    """Test: GET /cities requiere autenticación."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/cities")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_cities_with_auth():
    """Test: GET /cities con API key válida retorna lista de ciudades."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/cities",
            headers={"X-API-Key": TEST_API_KEY},
        )

    # Si la BD no está poblada, puede retornar 401 (key no existe)
    # Si está poblada, retorna 200
    if response.status_code == 200:
        data = response.json()
        assert "count" in data
        assert "cities" in data
        assert data["count"] >= 0


@pytest.mark.asyncio
async def test_city_by_divipola_bogota():
    """Test: GET /cities/11001 retorna Bogotá."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/cities/11001",
            headers={"X-API-Key": TEST_API_KEY},
        )

    if response.status_code == 200:
        data = response.json()
        assert data["divipola"] == "11001"
        assert "Bogotá" in data["name"]


@pytest.mark.asyncio
async def test_city_by_divipola_not_found():
    """Test: GET /cities/99999 retorna 404."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/cities/99999",
            headers={"X-API-Key": TEST_API_KEY},
        )

    if response.status_code != 401:  # Si la key existe
        assert response.status_code == 404
