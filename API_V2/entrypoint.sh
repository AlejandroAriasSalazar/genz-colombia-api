#!/bin/sh
set -eu

if [ -z "${DATABASE_URL:-}" ] && [ -n "${POSTGRES_HOST:-}" ]; then
  DATABASE_URL="$(python -c 'import os, urllib.parse; print("postgresql+psycopg://%s:%s@%s:%s/%s" % (urllib.parse.quote(os.environ["POSTGRES_USER"], safe=""), urllib.parse.quote(os.environ["POSTGRES_PASSWORD"], safe=""), os.environ["POSTGRES_HOST"], os.environ.get("POSTGRES_PORT", "5432"), os.environ["POSTGRES_DB"]))')"
  export DATABASE_URL
fi

python - <<'PY'
import os
import time

import psycopg

url = os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
for attempt in range(60):
    try:
        with psycopg.connect(url, connect_timeout=5):
            break
    except psycopg.OperationalError:
        if attempt == 59:
            raise
        time.sleep(2)
PY

case "${1:-api}" in
  api)
    alembic upgrade head
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 \
      --workers "${WEB_CONCURRENCY:-2}" --proxy-headers
    ;;
  worker)
    exec python -m app.worker
    ;;
  bootstrap)
    alembic upgrade head
    exec python -m scripts.bootstrap
    ;;
  *)
    exec "$@"
    ;;
esac
