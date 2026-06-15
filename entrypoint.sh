#!/bin/sh
set -eu

case "${1:-api}" in
  api)
    alembic upgrade head
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 \
      --workers "${WEB_CONCURRENCY:-2}" --proxy-headers
    ;;
  worker)
    exec python -m app.worker
    ;;
  *)
    exec "$@"
    ;;
esac
