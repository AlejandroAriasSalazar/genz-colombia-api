import json
import os
import re
import subprocess
import time
from pathlib import Path

import psycopg

from scripts.bootstrap import main as bootstrap_main

STATUS_PATH = Path(os.environ.get("RAW_STORAGE_PATH", "/data/raw")) / "bootstrap-status.json"


def write_status(status: str, phase: str, detail: str | None = None) -> None:
    payload = {"status": status, "phase": phase}
    if detail:
        sanitized = re.sub(r"://([^:@/]+):([^@/]+)@", r"://\1:<redacted>@", detail)
        payload["detail"] = sanitized[-2000:]
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATUS_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload))
    temporary.replace(STATUS_PATH)


def wait_for_database() -> None:
    url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
    schema = os.environ.get("POSTGRES_SCHEMA", "api_v2")
    for attempt in range(60):
        try:
            with psycopg.connect(url, connect_timeout=5, autocommit=True) as connection:
                quoted_schema = connection.execute(
                    "SELECT pg_catalog.quote_ident(%s)", (schema,)
                ).fetchone()[0]
                connection.execute(f"CREATE SCHEMA IF NOT EXISTS {quoted_schema}")
                return
        except psycopg.OperationalError:
            if attempt == 59:
                raise
            time.sleep(2)


def run_migrations() -> None:
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout).strip())


def main() -> None:
    try:
        write_status("running", "database")
        wait_for_database()
        write_status("running", "migrations")
        run_migrations()
        write_status("running", "dane_ingestion")
        bootstrap_main()
        write_status("complete", "published")
    except Exception as exc:
        write_status("failed", "bootstrap", f"{type(exc).__name__}: {exc}")
        raise


if __name__ == "__main__":
    main()
