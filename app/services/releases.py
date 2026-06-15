import hashlib
import shutil
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import DatasetVersion, DataSource, PopulationCell, ReleaseStatus, SourceSnapshot
from app.services.ingestion import DANEPopulationConnector
from app.services.quality import validate_population_cells
from app.services.source_manifest import read_manifest, source_from_manifest


def sync_source_manifest(db: Session, manifest_path: Path) -> DataSource:
    data = read_manifest(manifest_path)
    source = db.get(DataSource, data["id"])
    if source is None:
        source = source_from_manifest(data)
        db.add(source)
    else:
        for field in (
            "name",
            "owner",
            "official_url",
            "landing_page",
            "license_name",
            "connector",
            "refresh_frequency",
            "reference_period",
            "expected_schema",
        ):
            setattr(source, field, data[field])
    db.flush()
    return source


def create_candidate_release(
    db: Session,
    settings: Settings,
    manifest_path: Path,
    local_source: Path | None = None,
    years: set[int] | None = None,
) -> DatasetVersion:
    source = sync_source_manifest(db, manifest_path)
    connector = DANEPopulationConnector(settings)
    if local_source:
        digest = hashlib.sha256()
        with local_source.open("rb") as source_file:
            for chunk in iter(lambda: source_file.read(1024 * 1024), b""):
                digest.update(chunk)
        checksum = digest.hexdigest()
        byte_size = local_source.stat().st_size
        if byte_size > settings.source_max_bytes:
            raise ValueError("Source exceeds configured maximum size")
        immutable_dir = settings.raw_storage_path / source.id / checksum
        immutable_dir.mkdir(parents=True, exist_ok=True)
        download_path = immutable_dir / "source.xlsx"
        if not download_path.exists():
            shutil.copy2(local_source, download_path)
        etag = last_modified = None
    else:
        result = connector.download(source.official_url, source.id)
        checksum, download_path, byte_size = result.checksum, result.path, result.byte_size
        etag, last_modified = result.etag, result.last_modified

    snapshot = db.scalar(select(SourceSnapshot).where(SourceSnapshot.checksum_sha256 == checksum))
    if snapshot is None:
        snapshot = SourceSnapshot(
            source_id=source.id,
            checksum_sha256=checksum,
            storage_path=str(download_path),
            byte_size=byte_size,
            http_etag=etag,
            http_last_modified=last_modified,
        )
        db.add(snapshot)
        db.flush()

    target_years = years or set(range(2018, 2043))
    cells, controls = connector.parse(download_path, set(settings.target_municipalities), target_years)
    quality = validate_population_cells(
        cells, controls, set(settings.target_municipalities), target_years, settings.max_age
    )
    version_name = f"dane-{checksum[:12]}-m1"
    existing = db.scalar(select(DatasetVersion).where(DatasetVersion.version == version_name))
    if existing:
        return existing

    release = DatasetVersion(
        version=version_name,
        snapshot_id=snapshot.id,
        status=ReleaseStatus.candidate if quality["status"] == "passed" else ReleaseStatus.rejected,
        method_version="dane-xlsx-m1",
        reference_start=min(target_years),
        reference_end=max(target_years),
        row_count=len(cells),
        quality_report=quality,
    )
    db.add(release)
    db.flush()
    db.bulk_save_objects([PopulationCell(dataset_version_id=release.id, **cell.__dict__) for cell in cells])
    return release


def publish_release(db: Session, version: str) -> DatasetVersion:
    release = db.scalar(select(DatasetVersion).where(DatasetVersion.version == version))
    if release is None:
        raise ValueError(f"Unknown dataset version: {version}")
    if release.status == ReleaseStatus.rejected or release.quality_report.get("status") != "passed":
        raise ValueError("A failed or rejected release cannot be published")
    db.execute(
        update(DatasetVersion)
        .where(DatasetVersion.status == ReleaseStatus.published, DatasetVersion.id != release.id)
        .values(status=ReleaseStatus.superseded)
    )
    release.status = ReleaseStatus.published
    release.published_at = datetime.now(UTC)
    db.flush()
    return release
