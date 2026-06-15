from fastapi import APIRouter, Depends, Security
from sqlalchemy.orm import Session

from app.api.deps import get_current_client
from app.core.config import Settings, get_settings
from app.database import get_db
from app.models import ApiClient
from app.schemas import (
    AudienceProfileRequest,
    MarketReportRequest,
    MarketSizeRequest,
    TerritoryRankingRequest,
)
from app.services.market import audience_profile, market_size, territory_ranking
from app.services.query import release_metadata
from app.services.report import build_report

router = APIRouter(tags=["Market"])


@router.post("/market/size", summary="Market size for a target profile")
def size(
    payload: MarketSizeRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: ApiClient = Security(get_current_client, scopes=["market:read"]),
):
    release, result = market_size(db, settings, payload)
    return {"dataset": release_metadata(release), **result}


@router.post("/market/ranking", summary="Rank territories by target size (site selection)")
def ranking(
    payload: TerritoryRankingRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: ApiClient = Security(get_current_client, scopes=["market:read"]),
):
    release, year, items = territory_ranking(db, settings, payload)
    return {
        "dataset": release_metadata(release),
        "reference_year": year,
        "level": payload.level,
        "count": len(items),
        "results": items,
    }


@router.post("/market/profile", summary="Demographic profile of a territory or segment")
def profile(
    payload: AudienceProfileRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: ApiClient = Security(get_current_client, scopes=["market:read"]),
):
    release, result = audience_profile(db, settings, payload)
    return {"dataset": release_metadata(release), **result}


@router.post("/market/report", summary="Consolidated market-intelligence report (JSON)")
def report(
    payload: MarketReportRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: ApiClient = Security(get_current_client, scopes=["market:read"]),
):
    return build_report(
        db, settings, payload.municipality_code, payload.year, payload.age_min, payload.age_max
    )
