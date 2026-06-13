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

# Esperar a que PostgreSQL esté listo
echo "Waiting for database..."
MAX_RETRIES=30
RETRY_COUNT=0

until python -c "
import asyncio
import asyncpg
async def test():
    url = '${DATABASE_URL_SYNC}'.replace('postgresql://', '')
    # Parse: user:password@host:port/db
    try:
        conn = await asyncpg.connect('${DATABASE_URL_SYNC}')
        await conn.close()
        print('Database connected!')
    except Exception as e:
        print(f'Connection error: {e}')
        exit(1)
asyncio.run(test())
" 2>/dev/null; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo "ERROR: Could not connect to database after $MAX_RETRIES attempts"
    echo "Final DATABASE_URL_SYNC: $DATABASE_URL_SYNC"
    exit 1
  fi
  echo "Database unavailable - waiting... ($RETRY_COUNT/$MAX_RETRIES)"
  sleep 2
done

# Inicializar base de datos (crear tablas)
echo "Initializing database tables..."
python -c "
import asyncio
from app.database import init_db
asyncio.run(init_db())
print('Database tables created!')
"

# Verificar si hay datos (si no, ejecutar seed)
echo "Checking if seed data is needed..."
python -c "
import asyncio
from sqlalchemy import select
from app.database import async_session
from app.models.city import City

async def check():
    async with async_session() as session:
        result = await session.execute(select(City))
        cities = result.scalars().all()
        if not cities:
            print('No cities found - running seed data...')
            import subprocess
            result = subprocess.run(['python', '-m', 'scripts.seed_data'], capture_output=True, text=True)
            print(result.stdout)
            if result.stderr:
                print('STDERR:', result.stderr)
        else:
            print(f'Database already has {len(cities)} cities - skipping seed')

asyncio.run(check())
"

echo "=== Starting API Server ==="
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
