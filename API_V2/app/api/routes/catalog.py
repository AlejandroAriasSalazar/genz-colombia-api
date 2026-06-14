from fastapi import APIRouter, Depends, Security
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_client
from app.core.config import Settings, get_settings
from app.database import get_db
from app.models import ApiClient, DatasetVersion, DataSource, PopulationCell
from app.services.query import release_metadata, resolve_release

router = APIRouter(tags=["Catalog"])


@router.get("/metadata", summary="Dataset and methodological metadata")
def metadata(settings: Settings = Depends(get_settings)):
    return {
        "api_version": settings.app_version,
        "dataset_name": "GenZ Colombia - base demográfica sintética",
        "nature": "Synthetic persons sampled from official aggregate population projections",
        "core_variables": ["age", "sex", "municipality_code", "reference_year"],
        "excluded_unvalidated_variables": [
            "music_interest",
            "technology_interest",
            "bicycle_use",
            "socioeconomic_stratum",
            "education",
            "occupation",
            "internet_access",
        ],
        "target_population": {
            "default_age_range": [12, 28],
            "municipalities": ["05001", "11001"],
            "default_reference_year": settings.default_reference_year,
        },
        "method": {
            "sampling": "Deterministic weighted sampling from DANE municipality-sex-age cells",
            "identifiers": "HMAC-derived synthetic identifiers; never source identifiers",
            "privacy": f"Aggregate cells below {settings.small_cell_threshold} are suppressed",
        },
    }


@router.get("/sources", summary="Registered official data sources")
def sources(db: Session = Depends(get_db)):
    rows = db.scalars(select(DataSource).order_by(DataSource.id)).all()
    return {
        "count": len(rows),
        "sources": [
            {
                "id": row.id,
                "name": row.name,
                "owner": row.owner,
                "official_url": row.official_url,
                "landing_page": row.landing_page,
                "license": row.license_name,
                "connector": row.connector,
                "refresh_frequency": row.refresh_frequency,
                "reference_period": row.reference_period,
            }
            for row in rows
        ],
    }


@router.get("/versions", summary="Dataset release history")
def versions(db: Session = Depends(get_db)):
    rows = db.scalars(select(DatasetVersion).order_by(DatasetVersion.created_at.desc())).all()
    return {
        "count": len(rows),
        "versions": [
            {
                "version": row.version,
                "status": row.status,
                "method_version": row.method_version,
                "reference_period": [row.reference_start, row.reference_end],
                "row_count": row.row_count,
                "created_at": row.created_at,
                "published_at": row.published_at,
            }
            for row in rows
        ],
    }


@router.get("/quality/{version}", summary="Quality gate report for a release")
def quality(version: str, db: Session = Depends(get_db)):
    release = resolve_release(db, version)
    return {"dataset": release_metadata(release), "quality_report": release.quality_report}


@router.get("/cities", summary="Cities available in the published release")
def cities(
    year: int | None = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: ApiClient = Security(get_current_client, scopes=["aggregate:read"]),
):
    release = resolve_release(db)
    reference_year = year or settings.default_reference_year
    rows = db.execute(
        select(
            PopulationCell.municipality_code,
            PopulationCell.municipality_name,
            PopulationCell.department_code,
            PopulationCell.department_name,
            func.sum(PopulationCell.population).label("population_total"),
        )
        .where(
            PopulationCell.dataset_version_id == release.id,
            PopulationCell.year == reference_year,
        )
        .group_by(
            PopulationCell.municipality_code,
            PopulationCell.municipality_name,
            PopulationCell.department_code,
            PopulationCell.department_name,
        )
        .order_by(PopulationCell.municipality_code)
    ).all()
    return {
        "dataset": release_metadata(release),
        "reference_year": reference_year,
        "count": len(rows),
        "cities": [row._mapping for row in rows],
    }
