from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import PLAIN_KEY, seed_database


def test_rate_limit_is_enforced():
    seed_database(request_limit=2)
    with TestClient(app) as client:
        headers = {"X-API-Key": PLAIN_KEY}
        assert client.get("/api/v2/cities", headers=headers).status_code == 200
        assert client.get("/api/v2/cities", headers=headers).status_code == 200
        response = client.get("/api/v2/cities", headers=headers)
        assert response.status_code == 429


def test_invalid_key_is_rejected(client):
    response = client.get("/api/v2/cities", headers={"X-API-Key": "gzv2_abcdef123456_wrong"})
    assert response.status_code == 401


def test_request_id_validation(client):
    response = client.get("/api/v2/health/live", headers={"X-Request-ID": "not-a-uuid"})
    assert response.status_code == 400


def test_unknown_fields_are_rejected(client, auth_headers):
    response = client.post(
        "/api/v2/population/sample",
        json={"sample_size": 2, "interes_musical": "inventado"},
        headers=auth_headers,
    )
    assert response.status_code == 422
