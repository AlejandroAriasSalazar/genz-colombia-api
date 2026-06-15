from fastapi import APIRouter, Depends, Query, Security
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_client
from app.core.config import Settings, get_settings
from app.core.plans import PLANS
from app.database import get_db
from app.models import ApiClient, DatasetVersion, DataSource, PopulationCell, ReleaseStatus
from app.services.enrichment import ENRICHMENT_MODEL_VERSION, public_dictionary
from app.services.query import release_metadata, resolve_release

router = APIRouter(tags=["Catalog"])

# Transparency differentiator: every variable carries its tier, source and status.
# Tier 1 = oficial DANE (reconciliado); Tier 2/3 = bloque de enriquecimiento (52 vars).
_TIER1 = [
    {"name": "municipality_code", "tier": 1, "source": "DANE proyecciones", "truth_granularity": "municipal", "method": "official", "status": "active"},
    {"name": "sex", "tier": 1, "source": "DANE proyecciones", "truth_granularity": "municipal", "method": "official", "status": "active"},
    {"name": "age", "tier": 1, "source": "DANE proyecciones", "truth_granularity": "municipal", "method": "official", "status": "active"},
    {"name": "reference_year", "tier": 1, "source": "DANE proyecciones", "truth_granularity": "municipal", "method": "official", "status": "active"},
]


def variable_dictionary() -> list[dict]:
    """Tier 1 oficial + las 52 variables de enriquecimiento (Tier 2/3)."""
    return _TIER1 + public_dictionary()


@router.get("/metadata", summary="Dataset and methodological metadata")
def metadata(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    coverage = (
        settings.target_municipalities
        if settings.target_municipalities
        else "all_municipalities"
    )
    municipality_count = department_count = None
    release = db.scalar(
        select(DatasetVersion.id)
        .where(DatasetVersion.status == ReleaseStatus.published)
        .order_by(DatasetVersion.published_at.desc())
        .limit(1)
    )
    if release is not None:
        municipality_count = db.scalar(
            select(func.count(func.distinct(PopulationCell.municipality_code))).where(
                PopulationCell.dataset_version_id == release
            )
        )
        department_count = db.scalar(
            select(func.count(func.distinct(PopulationCell.department_code))).where(
                PopulationCell.dataset_version_id == release
            )
        )
    return {
        "api_version": settings.app_version,
        "dataset_name": "GenZ Colombia - base demográfica sintética",
        "nature": "Synthetic persons sampled from official aggregate population projections",
        "core_variables": ["age", "sex", "municipality_code", "reference_year"],
        "enrichment": {
            "model_version": ENRICHMENT_MODEL_VERSION,
            "variable_count": 52,
            "access": "scope enrich:read (Pro/Enterprise); detalle en /enrichment/dictionary",
            "note": (
                "Tier 2 anclado a marginal local (IPF); Tier 3 modelado de encuesta "
                "(cópula/condicional), verdad regional y banda de confianza. Tier 3 no se "
                "publica a municipal sin validación externa."
            ),
        },
        "target_population": {
            "default_age_range": [12, 28],
            "coverage": coverage,
            "municipality_count": municipality_count,
            "department_count": department_count,
            "default_reference_year": settings.default_reference_year,
        },
        "variables": variable_dictionary(),
        "method": {
            "technique": (
                "Capa demográfica (Tier 1): remuestreo Monte Carlo por inverso de CDF de "
                "las celdas marginales oficiales DANE (municipio x sexo x edad). Capa de "
                "enriquecimiento (V3): síntesis de población — IPF anclado a marginales "
                "locales para Tier 2 y cópula gaussiana + modelos condicionales para la "
                "distribución conjunta de las variables Tier 3, con incertidumbre cuantificada."
            ),
            "joint_distribution": (
                "Sí se modela una distribución conjunta para el bloque enriquecido, "
                "condicionada a la demografía oficial como restricción dura (los totales "
                "DANE no se alteran)."
            ),
            "sampling": "Deterministic weighted sampling from DANE municipality-sex-age cells",
            "reproducibility": (
                "Same seed + dataset version + enrichment model version yields the same "
                "multivariable sample across environments"
            ),
            "identifiers": "HMAC-derived synthetic identifiers; never source identifiers",
            "privacy": f"Aggregate cells below {settings.small_cell_threshold} are suppressed",
            "validation_gate": (
                "Tier 3 a municipal requiere validación externa contra fuente local "
                "independiente; sin ella se entrega como estimación regional con banda."
            ),
        },
    }


@router.get("/plans", summary="Commercial plans (pricing as data)")
def plans():
    return {
        "currency": "USD",
        "plans": [
            {
                "tier": tier,
                "label": plan["label"],
                "price_usd_month": plan["price_usd_month"],
                "limits": {
                    "requests_per_minute": plan["requests_per_minute"],
                    "requests_per_day": plan["requests_per_day"],
                    "max_sample_size": plan["max_sample_size"],
                },
                "scopes": plan["scopes"],
                "coverage": plan["coverage"],
                "includes": plan["includes"],
            }
            for tier, plan in PLANS.items()
        ],
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
    department_code: str | None = Query(None, pattern=r"^\d{2}$"),
    limit: int = Query(2000, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: ApiClient = Security(get_current_client, scopes=["aggregate:read"]),
):
    release = resolve_release(db)
    reference_year = year or settings.default_reference_year
    conditions = [
        PopulationCell.dataset_version_id == release.id,
        PopulationCell.year == reference_year,
    ]
    if department_code:
        conditions.append(PopulationCell.department_code == department_code)
    grouping = (
        PopulationCell.municipality_code,
        PopulationCell.municipality_name,
        PopulationCell.department_code,
        PopulationCell.department_name,
    )
    total = int(
        db.scalar(
            select(func.count(func.distinct(PopulationCell.municipality_code))).where(*conditions)
        )
        or 0
    )
    rows = db.execute(
        select(*grouping, func.sum(PopulationCell.population).label("population_total"))
        .where(*conditions)
        .group_by(*grouping)
        .order_by(PopulationCell.municipality_code)
        .limit(limit)
        .offset(offset)
    ).all()
    return {
        "dataset": release_metadata(release),
        "reference_year": reference_year,
        "pagination": {"limit": limit, "offset": offset, "total": total, "returned": len(rows)},
        "count": len(rows),
        "cities": [row._mapping for row in rows],
    }


@router.get("/departments", summary="Departments available in the published release")
def departments(
    year: int | None = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: ApiClient = Security(get_current_client, scopes=["aggregate:read"]),
):
    release = resolve_release(db)
    reference_year = year or settings.default_reference_year
    rows = db.execute(
        select(
            PopulationCell.department_code,
            PopulationCell.department_name,
            func.count(func.distinct(PopulationCell.municipality_code)).label("municipality_count"),
            func.sum(PopulationCell.population).label("population_total"),
        )
        .where(
            PopulationCell.dataset_version_id == release.id,
            PopulationCell.year == reference_year,
        )
        .group_by(PopulationCell.department_code, PopulationCell.department_name)
        .order_by(PopulationCell.department_code)
    ).all()
    return {
        "dataset": release_metadata(release),
        "reference_year": reference_year,
        "count": len(rows),
        "departments": [row._mapping for row in rows],
    }
