import hmac
import json
import os
from contextlib import suppress
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.database import get_db
from app.models import DatasetVersion, ReleaseStatus

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/live", summary="Process liveness")
def liveness(settings: Settings = Depends(get_settings)):
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}


@router.get("/ready", summary="Dependency and dataset readiness")
def readiness(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    checks = {"database": False, "quota_backend": False, "published_dataset": False}
    try:
        db.execute(select(1))
        checks["database"] = True
        checks["published_dataset"] = (
            db.scalar(
                select(DatasetVersion.id).where(DatasetVersion.status == ReleaseStatus.published).limit(1)
            )
            is not None
        )
    except Exception:
        pass
    with suppress(Exception):
        checks["quota_backend"] = request.app.state.quota.ping()
    required = ["database", "quota_backend"]
    if settings.environment == "production":
        required.append("published_dataset")
    ready = all(checks[name] for name in required)
    return {"status": "ready" if ready else "not_ready", "checks": checks}


@router.get("/bootstrap", include_in_schema=False)
def bootstrap_status(
    x_operations_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
):
    expected = os.environ.get("BOOTSTRAP_API_KEY", "")
    if not expected or not x_operations_key or not hmac.compare_digest(expected, x_operations_key):
        raise HTTPException(status_code=404)
    path = Path(settings.raw_storage_path) / "bootstrap-status.json"
    if not path.exists():
        return {"status": "pending", "phase": "not_started"}
    return json.loads(path.read_text())
