from fastapi import APIRouter, Depends, Request, Security
from sqlalchemy.orm import Session

from app.api.deps import get_current_client
from app.core.config import Settings, get_settings
from app.core.errors import ProblemError
from app.database import get_db
from app.models import ApiClient
from app.schemas import AggregateRequest, AggregateResponse, SampleRequest, SampleResponse
from app.services.enrichment import ENRICHMENT_MODEL_VERSION, enrich_person
from app.services.query import aggregate_population, generate_sample, release_metadata

router = APIRouter(tags=["Population"])


def quota_headers(request: Request) -> dict[str, str]:
    quota = request.state.quota
    return {
        "X-RateLimit-Minute-Remaining": str(quota.minute_remaining),
        "X-RateLimit-Day-Remaining": str(quota.day_remaining),
    }


@router.post(
    "/population/sample", response_model=SampleResponse, summary="Generate a reproducible synthetic sample"
)
def sample(
    payload: SampleRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    client: ApiClient = Security(get_current_client, scopes=["sample:read"]),
):
    if payload.sample_size > client.max_sample_size:
        raise ProblemError(
            403,
            "Sample limit exceeded",
            f"This client may request at most {client.max_sample_size} records.",
        )
    enrichment_version = None
    if payload.enrich and "enrich:read" not in client.scopes:
        raise ProblemError(
            403,
            "Insufficient scope",
            "Enrichment requires the 'enrich:read' scope (Pro/Enterprise plans).",
        )
    release, persons = generate_sample(db, settings, payload)
    if payload.enrich:
        enrichment_version = ENRICHMENT_MODEL_VERSION
        domains = set(payload.enrich_domains) if payload.enrich_domains else None
        for person in persons:
            person["enrichment"] = enrich_person(person, domains)["attributes"]
    return SampleResponse(
        count=len(persons),
        seed=payload.seed,
        filters_applied=payload.filters.model_dump(exclude_none=True),
        dataset=release_metadata(release),
        enrichment_model_version=enrichment_version,
        persons=persons,
    )


@router.post(
    "/aggregate/query", response_model=AggregateResponse, summary="Query official population aggregates"
)
def aggregate(
    payload: AggregateRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: ApiClient = Security(get_current_client, scopes=["aggregate:read"]),
):
    release, total, pagination, results = aggregate_population(db, settings, payload)
    return AggregateResponse(
        metric=payload.metric,
        group_by=payload.group_by,
        filters_applied=payload.filters.model_dump(exclude_none=True),
        dataset=release_metadata(release),
        total_population=total,
        pagination=pagination,
        results=results,
    )
