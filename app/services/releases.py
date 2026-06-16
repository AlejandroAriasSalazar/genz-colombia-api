import csv
import gzip
import hashlib
import json
import shutil
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import DatasetVersion, DataSource, PopulationCell, ReleaseStatus, SourceSnapshot
from app.services.ingestion import DANEPopulationConnector, ParsedCell
from app.services.quality import IncrementalQualityGate
from app.services.source_manifest import read_manifest, source_from_manifest

DEFAULT_MANIFEST = Path("config/sources/dane_population_projections.yaml")


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

    version_name = f"dane-{checksum[:12]}-m1"
    existing = db.scalar(select(DatasetVersion).where(DatasetVersion.version == version_name))
    if existing:
        # This exact source snapshot was already ingested. Skip the (expensive) parse
        # entirely so a worker restart never re-reads the whole national file.
        return existing

    target_years = years or set(range(2018, 2043))
    municipalities = set(settings.target_municipalities)

    # Pass 1 — stream the source to validate and count without materializing it.
    gate = IncrementalQualityGate(municipalities, target_years, settings.max_age)
    matched = False
    for row_cells, control_key, control_value in connector.iter_cells(
        download_path, municipalities, target_years
    ):
        matched = True
        gate.observe_row(row_cells, control_key, control_value)
    if not matched:
        raise ValueError("No rows matched the configured municipalities and years")
    quality = gate.report()

    release = DatasetVersion(
        version=version_name,
        snapshot_id=snapshot.id,
        status=ReleaseStatus.candidate if quality["status"] == "passed" else ReleaseStatus.rejected,
        method_version="dane-xlsx-m1",
        reference_start=min(target_years),
        reference_end=max(target_years),
        row_count=gate.cell_count,
        quality_report=quality,
    )
    db.add(release)
    db.flush()

    # Pass 2 — stream again and insert in bounded batches. Never holds more than
    # `ingest_batch_size` rows in memory, so national ingestion fits in a small container.
    batch: list[dict] = []
    batch_size = settings.ingest_batch_size
    for row_cells, _control_key, _control_value in connector.iter_cells(
        download_path, municipalities, target_years
    ):
        for cell in row_cells:
            batch.append({"dataset_version_id": release.id, **cell.__dict__})
        if len(batch) >= batch_size:
            db.execute(insert(PopulationCell), batch)
            batch.clear()
    if batch:
        db.execute(insert(PopulationCell), batch)
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


# ---------------------------------------------------------------------------
# Carga de releases PRECOMPILADOS (la ruta recomendada en producción).
#
# El parse del XLSX de 131 MB se hace UNA vez, fuera de producción, con
# scripts/build_dataset.py, que deja un artefacto compacto (cells.csv.gz +
# controls.csv.gz + release.json). Aquí solo se valida (mismo gate) y se carga
# por COPY — segundos y unos pocos MB de RAM. Producción nunca parsea la fuente.
# ---------------------------------------------------------------------------

CELL_COLUMNS = (
    "dataset_version_id",
    "department_code",
    "department_name",
    "municipality_code",
    "municipality_name",
    "year",
    "area",
    "sex",
    "age",
    "population",
)


def _iter_artifact_cells(cells_path: Path) -> Iterator[ParsedCell]:
    """Stream ``ParsedCell`` rows from the gzipped artifact one at a time.

    Loading a release must never hold the whole national table in RAM: a multi-year,
    whole-population artifact is millions of rows, and materializing it into a list (plus
    the two full-dataset sets the old eager validator built) was OOM-killing the API
    container on the shared box at boot, since ``entrypoint.sh`` runs ``load-release`` on
    every deploy. Yielding keeps peak memory flat regardless of artifact size; callers
    that need two passes (validate, then insert) just iterate twice — gzip reads are cheap
    next to the original XLSX parse, which production never does.
    """
    with gzip.open(cells_path, "rt", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            yield ParsedCell(
                department_code=row["department_code"],
                department_name=row["department_name"],
                municipality_code=row["municipality_code"],
                municipality_name=row["municipality_name"],
                year=int(row["year"]),
                area=row["area"],
                sex=row["sex"],
                age=int(row["age"]),
                population=int(row["population"]),
            )


def _read_artifact_controls(controls_path: Path) -> dict[tuple[str, int, str], dict]:
    controls: dict[tuple[str, int, str], dict] = {}
    with gzip.open(controls_path, "rt", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            controls[(row["municipality_code"], int(row["year"]), row["area"])] = {
                "total": int(row["total"]),
                "M": int(row["M"]),
                "F": int(row["F"]),
            }
    return controls


def _insert_cells(db: Session, release_id: str, cells: Iterable[ParsedCell], batch_size: int) -> None:
    """Insert cells with Postgres COPY when available, else bounded batches (sqlite/tests).

    ``cells`` may be a generator: both branches consume it lazily, so a streamed artifact
    is never materialized in full."""
    if db.get_bind().dialect.name == "postgresql":
        dbapi_conn = db.connection().connection
        raw = getattr(dbapi_conn, "driver_connection", dbapi_conn)
        columns = ", ".join(CELL_COLUMNS)
        with raw.cursor() as cursor:
            with cursor.copy(f"COPY population_cells ({columns}) FROM STDIN") as copy:
                for cell in cells:
                    copy.write_row(
                        [
                            release_id,
                            cell.department_code,
                            cell.department_name,
                            cell.municipality_code,
                            cell.municipality_name,
                            cell.year,
                            cell.area,
                            cell.sex,
                            cell.age,
                            cell.population,
                        ]
                    )
        return
    batch: list[dict] = []
    for cell in cells:
        batch.append({"dataset_version_id": release_id, **cell.__dict__})
        if len(batch) >= batch_size:
            db.execute(insert(PopulationCell), batch)
            batch.clear()
    if batch:
        db.execute(insert(PopulationCell), batch)


def load_release(
    db: Session,
    settings: Settings,
    release_dir: Path,
    manifest_path: Path = DEFAULT_MANIFEST,
) -> DatasetVersion:
    """Load a prebuilt compact release into the database (idempotent).

    Re-runs the same quality gate as live ingestion, then loads via COPY. Returns
    the (candidate or rejected) release; publishing is a separate explicit step.
    """
    manifest = json.loads((release_dir / "release.json").read_text(encoding="utf-8"))
    version = manifest["version"]

    existing = db.scalar(select(DatasetVersion).where(DatasetVersion.version == version))
    if existing is not None:
        return existing

    source = sync_source_manifest(db, manifest_path)
    checksum = manifest["source_checksum_sha256"]
    snapshot = db.scalar(select(SourceSnapshot).where(SourceSnapshot.checksum_sha256 == checksum))
    if snapshot is None:
        snapshot = SourceSnapshot(
            source_id=source.id,
            checksum_sha256=checksum,
            storage_path=str(release_dir),
            byte_size=manifest["source_byte_size"],
        )
        db.add(snapshot)
        db.flush()

    artifacts = manifest["artifacts"]
    cells_path = release_dir / artifacts["cells"]
    # controls.csv.gz is small (one row per municipality-year-area, not per cell), so it
    # can stay in memory; the cells themselves are streamed.
    controls = _read_artifact_controls(release_dir / artifacts["controls"])
    years = set(manifest["years"])
    max_age = manifest.get("max_age", settings.max_age)

    # Pass 1 — validate by streaming the cells past an incremental gate, so peak memory
    # stays flat instead of building the cell list + two full-dataset sets the old eager
    # validator needed (the boot-time OOM). Empty municipality set -> completeness is
    # checked against the municipalities the artifact actually carries (it defines its
    # own served scope).
    gate = IncrementalQualityGate(set(), years, max_age)
    gate.register_controls(controls)
    for cell in _iter_artifact_cells(cells_path):
        gate.observe_cell(cell)
    quality = gate.report()

    release = DatasetVersion(
        version=version,
        snapshot_id=snapshot.id,
        status=ReleaseStatus.candidate if quality["status"] == "passed" else ReleaseStatus.rejected,
        method_version=manifest["method_version"],
        reference_start=manifest["reference_start"],
        reference_end=manifest["reference_end"],
        row_count=manifest["row_count"],
        quality_report=quality,
    )
    db.add(release)
    db.flush()
    # Pass 2 — stream the artifact a second time straight into COPY/batches; never a list.
    _insert_cells(db, release.id, _iter_artifact_cells(cells_path), settings.ingest_batch_size)
    return release


def latest_release_dir(root: Path) -> Path | None:
    """Newest release directory under ``root`` (by version name), or None."""
    candidates = [p for p in root.glob("*") if (p / "release.json").is_file()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.name)
