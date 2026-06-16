import argparse
import ctypes
import ctypes.util
import gc
import logging
import random
import signal
import threading
from pathlib import Path

from app.core.config import get_settings
from app.database import SessionLocal
from app.services.releases import create_candidate_release, latest_release_dir, load_release

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("genz_api_v3.worker")
MANIFEST = Path("config/sources/dane_population_projections.yaml")

_stop = threading.Event()


def _handle_signal(signum, _frame) -> None:
    logger.info("worker_shutdown_requested signal=%s", signum)
    _stop.set()


def _release_memory() -> None:
    """Hand freed heap back to the OS so an idle worker stays small.

    CPython keeps freed arenas in its own allocator and glibc keeps per-thread
    arenas around, so after a heavy parse the worker's RSS stays pinned near its
    peak for the whole (weekly) idle stretch. ``gc.collect()`` drops cycles and a
    best-effort ``malloc_trim`` (no-op off glibc) returns the pages, keeping the
    worker's footprint near zero between runs on the shared box.
    """
    gc.collect()
    try:
        libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6")
        if hasattr(libc, "malloc_trim"):
            libc.malloc_trim(0)
    except (OSError, AttributeError):  # non-glibc / no libc — nothing to trim
        pass


def run_once() -> None:
    """Heavy path: re-download and stream-parse the national source into a new release.

    Streamed end to end (``iter_cells`` generator + batched/COPY inserts), so peak
    memory stays bounded to one municipality-year instead of the whole country. This
    only runs when WORKER_AUTO_INGEST is enabled; production normally refreshes data
    offline via scripts/build_dataset.py + ``manage load-release``.
    """
    settings = get_settings()
    with SessionLocal.begin() as db:
        release = create_candidate_release(db, settings, MANIFEST)
        logger.info(
            "ingestion_complete version=%s status=%s", release.version, release.status.value
        )
    _release_memory()


def load_latest_release() -> None:
    """Low-RAM refresh: stream the newest prebuilt artifact in via COPY (idempotent).

    Costs a few MB regardless of dataset size and never touches the 131 MB XLSX, so
    it's safe to run unattended on the shared box. A no-op when no artifact is present
    or the latest one is already loaded.
    """
    settings = get_settings()
    release_dir = latest_release_dir(settings.data_releases_path)
    if release_dir is None:
        logger.info("no_prebuilt_release path=%s", settings.data_releases_path)
        return
    with SessionLocal.begin() as db:
        release = load_release(db, settings, release_dir)
        logger.info(
            "release_synced version=%s status=%s", release.version, release.status.value
        )
    _release_memory()


def _cycle(first: bool) -> None:
    """One scheduler cycle.

    The heavy national parse is opt-in (``worker_auto_ingest``) and must never run as a
    side effect of a deploy/restart: on the first cycle it only runs when
    ``worker_ingest_on_start`` is also set. Otherwise every cycle does the low-memory
    prebuilt-artifact sync, so the worker can never balloon and OOM the box.
    """
    settings = get_settings()
    heavy = settings.worker_auto_ingest and (settings.worker_ingest_on_start or not first)
    if heavy:
        run_once()
    else:
        load_latest_release()


def run_forever() -> None:
    settings = get_settings()
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)
    interval = settings.ingestion_interval_seconds

    first = True
    while not _stop.is_set():
        try:
            _cycle(first)
        except Exception:
            logger.exception("worker_cycle_failed")
        first = False
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
