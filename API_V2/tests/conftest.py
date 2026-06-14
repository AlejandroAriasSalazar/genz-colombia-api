import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEST_DB = Path("/tmp/genz_api_v2_test.db")
TEST_DB.unlink(missing_ok=True)
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["API_KEY_PEPPER"] = "test-pepper-with-sufficient-entropy"
os.environ["SYNTHETIC_ID_SECRET"] = "test-id-secret-with-sufficient-entropy"
os.environ["DEFAULT_REFERENCE_YEAR"] = "2026"

from app.core.config import get_settings
from app.core.security import digest_api_key
from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import (
    ApiClient,
    DatasetVersion,
    DataSource,
    PopulationCell,
    ReleaseStatus,
    SourceSnapshot,
)

PLAIN_KEY = "gzv2_abcdef123456_test-secret-value"


def seed_database(request_limit: int = 100) -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal.begin() as db:
        source = DataSource(
            id="dane_test",
            name="DANE test projection",
            owner="DANE",
            official_url="https://example.test/source.xlsx",
            landing_page="https://example.test",
            license_name="Open data",
            connector="dane_xlsx",
            refresh_frequency="weekly",
            reference_period="2026",
            expected_schema={"sheet": "PobMunicipalxÁreaSexoEdad"},
        )
        db.add(source)
        db.flush()
        snapshot = SourceSnapshot(
            source_id=source.id,
            checksum_sha256="a" * 64,
            storage_path="/tmp/source.xlsx",
            byte_size=123,
        )
        db.add(snapshot)
        db.flush()
        release = DatasetVersion(
            version="test-2026-m1",
            snapshot_id=snapshot.id,
            status=ReleaseStatus.published,
            method_version="test-m1",
            reference_start=2026,
            reference_end=2026,
            row_count=404,
            quality_report={"status": "passed", "checks": {"source_total_reconciliation": True}},
            published_at=datetime.now(UTC),
        )
        db.add(release)
        db.flush()
        for municipality, name, department, department_name in (
            ("05001", "Medellín", "05", "Antioquia"),
            ("11001", "Bogotá, D.C.", "11", "Bogotá, D.C."),
        ):
            for sex in ("M", "F"):
                for age in range(101):
                    db.add(
                        PopulationCell(
                            dataset_version_id=release.id,
                            department_code=department,
                            department_name=department_name,
                            municipality_code=municipality,
                            municipality_name=name,
                            year=2026,
                            area="Total",
                            sex=sex,
                            age=age,
                            population=10 + age + (5 if sex == "F" else 0),
                        )
                    )
        db.add(
            ApiClient(
                name="Test client",
                key_prefix="abcdef123456",
                key_digest=digest_api_key(PLAIN_KEY, get_settings().api_key_pepper),
                tier="free",
                scopes=["sample:read", "aggregate:read"],
                requests_per_minute=request_limit,
                requests_per_day=1000,
                max_sample_size=100,
            )
        )


@pytest.fixture
def client():
    seed_database()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers():
    return {"X-API-Key": PLAIN_KEY}
