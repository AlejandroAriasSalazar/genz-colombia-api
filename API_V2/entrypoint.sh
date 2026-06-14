#!/bin/sh
set -eu

if [ -z "${DATABASE_URL:-}" ] && [ -n "${POSTGRES_HOST:-}" ]; then
  DATABASE_URL="$(python -c 'import base64, os, urllib.parse; encoded = os.environ["POSTGRES_PASSWORD_B64"]; password = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)).decode(); print("postgresql+psycopg://%s:%s@%s:%s/%s?%s" % (urllib.parse.quote(os.environ["POSTGRES_USER"], safe=""), urllib.parse.quote(password, safe=""), os.environ["POSTGRES_HOST"], os.environ.get("POSTGRES_PORT", "5432"), os.environ["POSTGRES_DB"], urllib.parse.urlencode({"options": "-csearch_path=" + os.environ.get("POSTGRES_SCHEMA", "api_v2")})))')"
  export DATABASE_URL
fi

case "${1:-api}" in
  api)
    exec uvicorn app.main:app --host 0.0.0.0 --port 8000 \
      --workers "${WEB_CONCURRENCY:-2}" --proxy-headers
    ;;
  worker)
    exec python -m app.worker
    ;;
  bootstrap)
    exec python -m scripts.run_bootstrap
    ;;
  *)
    exec "$@"
    ;;
esac
