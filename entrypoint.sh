#!/bin/bash
set -e

echo "=== GenZ Colombia API - Starting ==="

# Build database URL from individual components if not set
if [ -z "$DATABASE_URL_SYNC" ]; then
  export DATABASE_URL_SYNC="postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-genz_db_password_2026}@${POSTGRES_HOST:-c7h3xe10fowkdr29wirdogaw}:${POSTGRES_PORT:-5432}/${POSTGRES_DB:-genz_api}"
  echo "Built DATABASE_URL_SYNC from individual vars: $DATABASE_URL_SYNC"
fi

if [ -z "$DATABASE_URL" ]; then
  export DATABASE_URL="postgresql+asyncpg://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-genz_db_password_2026}@${POSTGRES_HOST:-c7h3xe10fowkdr29wirdogaw}:${POSTGRES_PORT:-5432}/${POSTGRES_DB:-genz_api}"
  echo "Built DATABASE_URL from individual vars"
fi

# Remove surrounding single quotes if present (Coolify bug)
DATABASE_URL_SYNC=$(echo "$DATABASE_URL_SYNC" | sed "s/^'//;s/'$//")
export DATABASE_URL_SYNC
DATABASE_URL=$(echo "$DATABASE_URL" | sed "s/^'//;s/'$//")
export DATABASE_URL

echo "DATABASE_URL_SYNC: $DATABASE_URL_SYNC"
echo "Starting uvicorn directly (skipping DB init for now)"

# Start API server directly - the app handles DB init itself
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --log-level debug
