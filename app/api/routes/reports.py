from fastapi import APIRouter, Depends, Path, Query, Security
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.api.deps import get_report_client
from app.core.config import Settings, get_settings
from app.database import get_db
from app.models import ApiClient
from app.services.report import build_report, render_report_html

router = APIRouter(tags=["Report"])


@router.get(
    "/report/{municipality_code}",
    summary="Server-rendered market report page (a report is one URL)",
    response_class=HTMLResponse,
    include_in_schema=False,
)
def report_page(
    municipality_code: str = Path(pattern=r"^\d{5}$"),
    year: int | None = Query(None, ge=2018, le=2042),
    age_min: int = Query(12, ge=0, le=100),
    age_max: int = Query(28, ge=0, le=100),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    _: ApiClient = Security(get_report_client),
):
    report = build_report(db, settings, municipality_code, year, age_min, min(max(age_max, age_min), 100))
    return HTMLResponse(render_report_html(report), headers={"Cache-Control": "no-store"})
