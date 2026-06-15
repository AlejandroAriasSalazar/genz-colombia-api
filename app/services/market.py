from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import PopulationCell
from app.schemas import AudienceProfileRequest, MarketSizeRequest, TerritoryRankingRequest
from app.services.query import apply_filters, resolve_release

LEVELS = {
    "municipality": (PopulationCell.municipality_code, PopulationCell.municipality_name),
    "department": (PopulationCell.department_code, PopulationCell.department_name),
}

# Age bands for an audience profile (pyramid). Only bands overlapping the filter survive.
PROFILE_BANDS = [(0, 11), (12, 14), (15, 17), (18, 20), (21, 24), (25, 28), (29, 39), (40, 59), (60, 100)]


def _resolved_filters(request, settings: Settings):
    filters = request.filters.model_copy()
    if filters.year is None:
        filters.year = settings.default_reference_year
    return filters


def _year_population(db: Session, release_id: str, year: int) -> int:
    statement = select(func.sum(PopulationCell.population)).where(
        PopulationCell.dataset_version_id == release_id, PopulationCell.year == year
    )
    return int(db.scalar(statement) or 0)


def market_size(db: Session, settings: Settings, request: MarketSizeRequest):
    """How many people match a target profile, and what share of the country they are."""
    release = resolve_release(db, request.dataset_version)
    filters = _resolved_filters(request, settings)
    target = int(db.scalar(apply_filters(select(func.sum(PopulationCell.population)), release.id, filters)) or 0)
    national = _year_population(db, release.id, filters.year)
    sex_rows = db.execute(
        apply_filters(
            select(PopulationCell.sex, func.sum(PopulationCell.population).label("p")), release.id, filters
        ).group_by(PopulationCell.sex)
    ).all()
    return release, {
        "reference_year": filters.year,
        "market_size": target,
        "national_population": national,
        "share_of_national_percent": round(target * 100 / national, 4) if national else 0.0,
        "by_sex": {row.sex: int(row.p) for row in sex_rows},
    }


def territory_ranking(db: Session, settings: Settings, request: TerritoryRankingRequest):
    """Rank territories by how much of the target profile they hold (site selection)."""
    release = resolve_release(db, request.dataset_version)
    filters = _resolved_filters(request, settings)
    code_col, name_col = LEVELS[request.level]
    target_rows = db.execute(
        apply_filters(
            select(
                code_col.label("code"),
                name_col.label("name"),
                func.sum(PopulationCell.population).label("target"),
            ),
            release.id,
            filters,
        ).group_by(code_col, name_col)
    ).all()
    total_rows = db.execute(
        select(code_col.label("code"), func.sum(PopulationCell.population).label("p"))
        .where(PopulationCell.dataset_version_id == release.id, PopulationCell.year == filters.year)
        .group_by(code_col)
    ).all()
    totals = {row.code: int(row.p) for row in total_rows}
    items = []
    for row in target_rows:
        target = int(row.target)
        base = totals.get(row.code, 0)
        items.append(
            {
                "code": row.code,
                "name": row.name,
                "target_size": target,
                "territory_population": base,
                "penetration_percent": round(target * 100 / base, 4) if base else 0.0,
            }
        )
    items.sort(key=lambda item: item["target_size"], reverse=True)
    return release, filters.year, items[: request.limit]


def _weighted_median_age(by_age: dict[int, int]) -> int | None:
    total = sum(by_age.values())
    if not total:
        return None
    half = total / 2
    cumulative = 0
    for age in sorted(by_age):
        cumulative += by_age[age]
        if cumulative >= half:
            return age
    return max(by_age)


def audience_profile(db: Session, settings: Settings, request: AudienceProfileRequest):
    """Profile the population of a territory/segment: sex split, age pyramid, median age."""
    release = resolve_release(db, request.dataset_version)
    filters = _resolved_filters(request, settings)
    rows = db.execute(
        apply_filters(
            select(
                PopulationCell.age,
                PopulationCell.sex,
                func.sum(PopulationCell.population).label("p"),
            ),
            release.id,
            filters,
        ).group_by(PopulationCell.age, PopulationCell.sex)
    ).all()
    total = 0
    by_sex: dict[str, int] = {"M": 0, "F": 0}
    by_age: dict[int, int] = {}
    for row in rows:
        population = int(row.p)
        total += population
        by_sex[row.sex] = by_sex.get(row.sex, 0) + population
        by_age[row.age] = by_age.get(row.age, 0) + population
    age_bands = [
        {"range": f"{lo}-{hi}", "count": sum(p for a, p in by_age.items() if lo <= a <= hi)}
        for lo, hi in PROFILE_BANDS
        if not (hi < filters.age_min or lo > filters.age_max)
    ]
    return release, {
        "reference_year": filters.year,
        "total": total,
        "by_sex": by_sex,
        "sex_ratio_female_percent": round(by_sex.get("F", 0) * 100 / total, 2) if total else 0.0,
        "median_age": _weighted_median_age(by_age),
        "age_bands": age_bands,
    }
