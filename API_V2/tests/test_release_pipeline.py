from contextlib import contextmanager
from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.core.rate_limit import RedisQuota
from app.core.security import generate_api_key, parse_key_prefix
from app.database import Base, SessionLocal, engine
from app.models import DatasetVersion, DataSource, PopulationCell, ReleaseStatus
from app.services.ingestion import DANEPopulationConnector
from app.services.releases import create_candidate_release, publish_release
from app.services.source_manifest import read_manifest
from tests.test_connector import build_fixture

MANIFEST = Path("config/sources/dane_population_projections.yaml")


def test_candidate_release_and_publication(tmp_path):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    source_file = tmp_path / "dane.xlsx"
    build_fixture(source_file)

    with SessionLocal.begin() as db:
        release = create_candidate_release(
            db,
            get_settings(),
            MANIFEST,
            local_source=source_file,
            years={2026},
        )
        assert release.status == ReleaseStatus.candidate
        assert release.row_count == 404
        assert release.quality_report["status"] == "passed"
        version = release.version

    with SessionLocal.begin() as db:
        published = publish_release(db, version)
        assert published.status == ReleaseStatus.published

    with SessionLocal() as db:
        assert db.scalar(select(DataSource.id)) == "dane_population_projections_municipal_2018_2042"
        assert db.scalar(select(DatasetVersion.status)) == ReleaseStatus.published
        assert db.scalar(select(PopulationCell).limit(1)) is not None


def test_rejected_release_cannot_be_published():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal.begin() as db:
        source = DataSource(
            id="failed",
            name="Failed",
            owner="DANE",
            official_url="https://example.test",
            landing_page="https://example.test",
            license_name="Open",
            connector="test",
            refresh_frequency="never",
            reference_period="none",
            expected_schema={},
        )
        db.add(source)
        from app.models import SourceSnapshot

        snapshot = SourceSnapshot(
            source_id="failed",
            checksum_sha256="f" * 64,
            storage_path="/tmp/failed",
            byte_size=0,
        )
        db.add(snapshot)
        db.flush()
        db.add(
            DatasetVersion(
                version="failed-v1",
                snapshot_id=snapshot.id,
                status=ReleaseStatus.rejected,
                method_version="test",
                reference_start=2026,
                reference_end=2026,
                quality_report={"status": "failed"},
            )
        )
    with SessionLocal.begin() as db, pytest.raises(ValueError, match="cannot be published"):
        publish_release(db, "failed-v1")


def test_manifest_validation(tmp_path):
    manifest = read_manifest(MANIFEST)
    assert manifest["owner"].startswith("Departamento Administrativo")
    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("id: incomplete\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing fields"):
        read_manifest(invalid)


def test_download_stream_is_checksummed_and_immutable(tmp_path, monkeypatch):
    content = b"real-source-bytes"

    class FakeResponse:
        headers = {"etag": "abc", "last-modified": "today"}

        def raise_for_status(self):
            return None

        def iter_bytes(self):
            yield content[:5]
            yield content[5:]

    @contextmanager
    def fake_stream(*args, **kwargs):
        yield FakeResponse()

    monkeypatch.setattr("app.services.ingestion.httpx.stream", fake_stream)
    settings = Settings(
        environment="test",
        database_url="sqlite://",
        raw_storage_path=tmp_path,
        source_max_bytes=100,
    )
    result = DANEPopulationConnector(settings).download("https://example.test/source", "source")
    assert result.path.read_bytes() == content
    assert result.byte_size == len(content)
    assert len(result.checksum) == 64


def test_redis_quota_contract_without_external_redis():
    class FakeRedis:
        def __init__(self, values):
            self.values = values

        def eval(self, *args):
            return self.values

        def ping(self):
            return True

    quota = RedisQuota.__new__(RedisQuota)
    quota.client = FakeRedis([1, 1])
    result = quota.consume("client", 2, 10)
    assert result.minute_remaining == 1
    assert quota.ping() is True

    quota.client = FakeRedis([3, 1])
    with pytest.raises(Exception, match="Quota exceeded"):
        quota.consume("client", 2, 10)


def test_api_key_format():
    key, prefix = generate_api_key()
    assert parse_key_prefix(key) == prefix
    assert parse_key_prefix("invalid") is None


def test_production_configuration_requires_real_dependencies():
    with pytest.raises(ValueError, match="Production requires PostgreSQL"):
        Settings(environment="production")
    with pytest.raises(ValueError, match="Production requires Redis"):
        Settings(
            environment="production",
            database_url="postgresql+psycopg://user:pass@db/name",
        )
