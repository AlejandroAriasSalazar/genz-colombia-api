import os
from pathlib import Path

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import digest_api_key, parse_key_prefix
from app.database import SessionLocal
from app.models import ApiClient
from app.services.releases import create_candidate_release, publish_release

MANIFEST = Path("config/sources/dane_population_projections.yaml")


def ensure_initial_client() -> None:
    plain_key = os.environ.get("BOOTSTRAP_API_KEY")
    if not plain_key:
        raise RuntimeError("BOOTSTRAP_API_KEY is required")
    prefix = parse_key_prefix(plain_key)
    if not prefix:
        raise RuntimeError("BOOTSTRAP_API_KEY has an invalid format")
    settings = get_settings()
    with SessionLocal.begin() as db:
        existing = db.scalar(select(ApiClient).where(ApiClient.key_prefix == prefix))
        if existing is None:
            db.add(
                ApiClient(
                    name="Production bootstrap client",
                    key_prefix=prefix,
                    key_digest=digest_api_key(plain_key, settings.api_key_pepper),
                    tier="enterprise",
                    scopes=["sample:read", "aggregate:read"],
                    requests_per_minute=3000,
                    requests_per_day=200000,
                    max_sample_size=1000,
                )
            )


def main() -> None:
    settings = get_settings()
    with SessionLocal.begin() as db:
        release = create_candidate_release(db, settings, MANIFEST)
        version = release.version
        quality_status = release.quality_report.get("status")
    if quality_status != "passed":
        raise RuntimeError(f"Release {version} failed its quality gate")
    with SessionLocal.begin() as db:
        publish_release(db, version)
    ensure_initial_client()
    print(f"bootstrap_complete release={version} quality=passed")


if __name__ == "__main__":
    main()
