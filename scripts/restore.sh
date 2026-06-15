#!/bin/sh
set -eu

: "${DATABASE_URL:?DATABASE_URL is required}"
: "${1:?Usage: restore.sh backup.dump}"
pg_restore --clean --if-exists --no-owner --dbname="$DATABASE_URL" "$1"
alembic upgrade head
