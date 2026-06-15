import random
from bisect import bisect_left
from itertools import accumulate

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import ProblemError
from app.core.security import stable_hmac_hex
from app.models import DatasetVersion, PopulationCell, ReleaseStatus
from app.schemas import AggregateRequest, PopulationFilters, SampleRequest


def resolve_release(db: Session, requested: str | None = None) -> DatasetVersion:
    statement = select(DatasetVersion)
    if requested:
        statement = statement.where(
            DatasetVersion.version == requested,
            DatasetVersion.status.in_([ReleaseStatus.published, ReleaseStatus.superseded]),
        )
    else:
        statement = statement.where(DatasetVersion.status == ReleaseStatus.published).order_by(
            DatasetVersion.published_at.desc()
        )
    release = db.scalar(statement.limit(1))
    if release is None:
        raise ProblemError(503, "Dataset unavailable", "No approved dataset release is available.")
    return release


def apply_filters(statement, release_id: str, filters: PopulationFilters):
    statement = statement.where(
        PopulationCell.dataset_version_id == release_id,
        PopulationCell.age >= filters.age_min,
        PopulationCell.age <= filters.age_max,
    )
    if filters.department_code:
        statement = statement.where(PopulationCell.department_code == filters.department_code)
    if filters.municipality_code:
        statement = statement.where(PopulationCell.municipality_code == filters.municipality_code)
    if filters.year:
        statement = statement.where(PopulationCell.year == filters.year)
    if filters.sex:
        statement = statement.where(PopulationCell.sex == filters.sex)
    return statement


def release_metadata(release: DatasetVersion) -> dict:
    return {
        "version": release.version,
        "method_version": release.method_version,
        "reference_period": [release.reference_start, release.reference_end],
        "published_at": release.published_at,
        "source_as_of": release.snapshot.retrieved_at,
        "source_checksum_sha256": release.snapshot.checksum_sha256,
    }


def generate_sample(
    db: Session, settings: Settings, request: SampleRequest
) -> tuple[DatasetVersion, list[dict]]:
    release = resolve_release(db, request.dataset_version)
    filters = request.filters.model_copy()
    if filters.year is None:
        filters.year = settings.default_reference_year
    # Order by stable data dimensions (not the database autoincrement id) so the same
    # seed reproduces the same sample across environments and re-ingestions.
    statement = apply_filters(select(PopulationCell), release.id, filters).order_by(
        PopulationCell.municipality_code,
        PopulationCell.year,
        PopulationCell.sex,
        PopulationCell.age,
    )
    cells = list(db.scalars(statement))
    weights = [cell.population for cell in cells]
    total = sum(weights)
    if not cells or total <= 0:
        raise ProblemError(404, "No population found", "No population cells match the requested filters.")

    cumulative = list(accumulate(weights))
    rng = random.Random(request.seed)
    persons = []
    for index in range(request.sample_size):
        draw = rng.randrange(total) + 1
        # O(log n) inverse-CDF lookup; identical selection to a linear scan but
        # scales to national samples (~226k cells) without per-draw O(n) cost.
        cell_index = bisect_left(cumulative, draw)
        cell = cells[cell_index]
        identity = (
            f"{release.version}:{request.seed}:{index}:"
            f"{cell.municipality_code}:{cell.year}:{cell.sex}:{cell.age}"
        )
        persons.append(
            {
                "synthetic_id": stable_hmac_hex(settings.synthetic_id_secret, identity),
                "age": cell.age,
                "sex": cell.sex,
                "municipality_code": cell.municipality_code,
                "municipality_name": cell.municipality_name,
                "reference_year": cell.year,
            }
        )
    return release, persons


GROUP_COLUMNS = {
    "municipality_code": PopulationCell.municipality_code,
    "department_code": PopulationCell.department_code,
    "year": PopulationCell.year,
    "age": PopulationCell.age,
    "sex": PopulationCell.sex,
}


def aggregate_population(db: Session, settings: Settings, request: AggregateRequest):
    release = resolve_release(db, request.dataset_version)
    filters = request.filters.model_copy()
    # Default to a single reference year to avoid silently summing all 25 projection
    # years — unless the caller is explicitly building a time series (group_by year).
    if filters.year is None and "year" not in request.group_by:
        filters.year = settings.default_reference_year

    columns = [GROUP_COLUMNS[field] for field in request.group_by]

    # True total across every matching cell, independent of pagination, so that
    # share_percent denominators and total_population stay correct across pages.
    total = int(db.scalar(apply_filters(select(func.sum(PopulationCell.population)), release.id, filters)) or 0)

    grouped = apply_filters(select(*columns), release.id, filters).group_by(*columns).subquery()
    total_groups = int(db.scalar(select(func.count()).select_from(grouped)) or 0)

    population_sum = func.sum(PopulationCell.population).label("population")
    statement = (
        apply_filters(select(*columns, population_sum), release.id, filters)
        .group_by(*columns)
        .order_by(*columns)
        .limit(request.limit)
        .offset(request.offset)
    )
    rows = db.execute(statement).all()
    results = []
    for row in rows:
        population = int(row.population)
        suppressed = population < settings.small_cell_threshold
        value: int | float | None
        if suppressed:
            value = None
        elif request.metric == "share_percent":
            value = round(population * 100 / total, 4) if total else 0.0
        else:
            value = population
        results.append(
            {
                "group": {field: getattr(row, field) for field in request.group_by},
                "value": value,
                "suppressed": suppressed,
            }
        )
    pagination = {
        "limit": request.limit,
        "offset": request.offset,
        "total_groups": total_groups,
        "returned": len(results),
    }
    return release, total, pagination, results
