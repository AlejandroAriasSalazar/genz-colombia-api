#!/bin/bash
set -e

echo "=== GenZ Colombia API - Starting ==="

# Esperar a que PostgreSQL esté listo
echo "Waiting for database..."
MAX_RETRIES=30
RETRY_COUNT=0

until python -c "
import sqlalchemy
try:
    engine = sqlalchemy.create_engine('$DATABASE_URL_SYNC')
    engine.connect()
    print('Database connected!')
except:
    exit(1)
" 2>/dev/null; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo "ERROR: Could not connect to database after $MAX_RETRIES attempts"
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
