import logging
import time
from pathlib import Path

from app.core.config import get_settings
from app.database import SessionLocal
from app.services.releases import create_candidate_release

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("genz_api_v2.worker")
MANIFEST = Path("config/sources/dane_population_projections.yaml")


def run() -> None:
    settings = get_settings()
    time.sleep(24 * 60 * 60)
    while True:
        try:
            with SessionLocal.begin() as db:
                release = create_candidate_release(db, settings, MANIFEST)
                logger.info("ingestion_complete version=%s status=%s", release.version, release.status.value)
        except Exception:
            logger.exception("ingestion_failed")
        time.sleep(7 * 24 * 60 * 60)


if __name__ == "__main__":
    run()
