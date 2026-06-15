import argparse
import logging
import random
import signal
import threading
from pathlib import Path

from app.core.config import get_settings
from app.database import SessionLocal
from app.services.releases import create_candidate_release

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("genz_api_v3.worker")
MANIFEST = Path("config/sources/dane_population_projections.yaml")

_stop = threading.Event()


def _handle_signal(signum, _frame) -> None:
    logger.info("worker_shutdown_requested signal=%s", signum)
    _stop.set()


def run_once() -> None:
    settings = get_settings()
    with SessionLocal.begin() as db:
        release = create_candidate_release(db, settings, MANIFEST)
        logger.info(
            "ingestion_complete version=%s status=%s", release.version, release.status.value
        )


def run_forever() -> None:
    settings = get_settings()
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    interval = settings.ingestion_interval_seconds
    while not _stop.is_set():
        try:
            run_once()
        except Exception:
            logger.exception("ingestion_failed")
        # +/-10% jitter so multiple workers never re-ingest in lockstep.
        jitter = interval * 0.1
        delay = max(1.0, interval + random.uniform(-jitter, jitter))
        # Interruptible sleep: a shutdown signal wakes us immediately.
        if _stop.wait(delay):
            break
    logger.info("worker_stopped")


def main() -> None:
    parser = argparse.ArgumentParser(description="GenZ Colombia API V3 ingestion worker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single ingestion and exit (for an external scheduler/cron).",
    )
    args = parser.parse_args()
    if args.once:
        run_once()
    else:
        run_forever()


if __name__ == "__main__":
    main()
