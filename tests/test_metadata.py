"""
Tests para el endpoint /metadata.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_metadata():
    """Test: GET /metadata retorna metadata completa."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metadata")

    assert response.status_code == 200
    data = response.json()

    # Verificar estructura
    assert "api_version" in data
    assert "dataset_name" in data
    assert "universo" in data
    assert "variables" in data
    assert "clasificaciones" in data
    assert "fuentes" in data
    assert "metodologia" in data

    # Verificar universo
    assert data["universo"]["poblacion_objetivo"] == "Generación Z colombiana"
    assert data["universo"]["rango_edad"]["min"] == 12
    assert data["universo"]["rango_edad"]["max"] == 28
    assert "Bogotá D.C." in data["universo"]["ciudades"]
    assert "Medellín" in data["universo"]["ciudades"]

    # Verificar variables
    assert "demograficas" in data["variables"]
    assert "geograficas" in data["variables"]
    assert "educativas" in data["variables"]
    assert "ocupacionales" in data["variables"]
    assert "conectividad" in data["variables"]
    assert "conductuales" in data["variables"]


@pytest.mark.asyncio
async def test_schema():
    """Test: GET /schema retorna esquema de entidades."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/schema")

    assert response.status_code == 200
    data = response.json()

    # Verificar estructura
    assert "entities" in data
    assert "relationships_summary" in data

    # Verificar entidades
    assert "cities" in data["entities"]
    assert "neighborhoods" in data["entities"]
    assert "persons" in data["entities"]
    assert "api_keys" in data["entities"]
    assert "subscriptions" in data["entities"]
    assert "query_logs" in data["entities"]
