# GenZ Colombia API V2

API de producción para consultar proyecciones demográficas oficiales y generar
personas sintéticas reproducibles de Bogotá y Medellín.

## Qué es real y qué es sintético

- **Real/oficial:** las celdas agregadas de población por municipio, año, sexo y
  edad provienen del XLSX publicado por DANE.
- **Sintético:** cada fila de `/population/sample` es una extracción ponderada de
  esas celdas. No corresponde a una persona real ni contiene un identificador de
  fuente.
- **No incluido:** estrato, educación, ocupación, conectividad, música, tecnología
  y bicicleta. V2 no los publica hasta disponer de fuentes y calibración
  verificables.

Fuente inicial: DANE, *Serie municipal de población por área, sexo y edad para
el periodo 2018-2042*, actualización publicada el 8 de agosto de 2025.

## Arquitectura

```text
DANE XLSX -> snapshot SHA-256 -> candidato -> quality gate -> release publicada
                                                        |
                         FastAPI <- PostgreSQL <- celdas oficiales
                              |
                    Redis quotas + audit log
```

La API nunca consulta DANE durante una solicitud del cliente. Si DANE no está
disponible, continúa sirviendo la última release aprobada.

## Inicio local

```bash
cp .env.example .env
docker compose up -d postgres redis
docker compose run --rm api alembic upgrade head
docker compose run --rm api python -m scripts.manage ingest
docker compose run --rm api python -m scripts.manage publish VERSION
docker compose run --rm api python -m scripts.manage create-key --name local
docker compose up -d api
```

La ingestión genera un candidato. La publicación es una operación explícita y
solo acepta candidatos cuyo reporte de calidad tenga estado `passed`.

## Endpoints

Públicos:

- `GET /api/v2/health/live`
- `GET /api/v2/health/ready`
- `GET /api/v2/metadata`
- `GET /api/v2/sources`
- `GET /api/v2/versions`
- `GET /api/v2/quality/{version}`

Autenticados con `X-API-Key`:

- `GET /api/v2/cities`
- `POST /api/v2/population/sample`
- `POST /api/v2/aggregate/query`

Ejemplo:

```bash
curl -X POST http://localhost:8000/api/v2/population/sample \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $GENZ_API_KEY" \
  -d '{
    "filters": {
      "municipality_code": "11001",
      "year": 2026,
      "age_min": 18,
      "age_max": 28
    },
    "sample_size": 50,
    "seed": 2026
  }'
```

## Calidad y seguridad

- Migraciones Alembic; el proceso web nunca crea o elimina el esquema.
- Snapshots inmutables identificados por SHA-256.
- Releases versionadas, reversibles y separadas de la ingestión.
- Reconciliación exacta contra totales de hombres, mujeres y total del XLSX.
- API keys de alta entropía almacenadas mediante HMAC-SHA256.
- Cuotas atómicas por minuto y día en Redis.
- Scopes, límite de muestra por tier y supresión de celdas pequeñas.
- Errores `application/problem+json` compatibles con RFC 9457.
- OpenAPI documenta `X-API-Key`.
- Logging de auditoría sin almacenar la clave ni la IP en texto plano.

## Verificación

```bash
make lint
make test
```

La suite incluye contrato HTTP, autenticación, cuotas, filtros, reproducibilidad,
conector XLSX, reconciliación, publicación, rollback de migraciones y smoke tests.
La integración PostgreSQL/Redis se ejecuta en CI.

Consultar [OPERATIONS.md](docs/OPERATIONS.md) para despliegue y recuperación, y
[ACCEPTANCE.md](docs/ACCEPTANCE.md) para los criterios de liberación.
