"""
GenZ Colombia API - Aplicación principal.
API privada de datos sintéticos de la Generación Z colombiana.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time

from app.config import settings
from app.database import init_db, close_db

# Import all models so SQLAlchemy can resolve relationships
from app.models.city import City
from app.models.neighborhood import Neighborhood
from app.models.person import Person
from app.models.api_key import APIKey
from app.models.subscription import Subscription
from app.models.query_log import QueryLog

from app.api.routes import health, metadata, cities, neighborhoods, population, aggregate
from app.api.middleware.auth import AuthMiddleware
from app.api.middleware.rate_limit import limiter, rate_limit_exceeded_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestiona el ciclo de vida de la aplicación."""
    # Startup
    await init_db()

    # Seed data if needed
    from sqlalchemy import select
    from app.database import async_session
    from app.models.city import City as CityModel
    from app.models.api_key import APIKey as APIKeyModel

    async with async_session() as session:
        # Check and seed cities/persons
        result = await session.execute(select(CityModel))
        cities = result.scalars().all()
        if not cities:
            print("No cities found - running seed data...")
            import subprocess
            import sys
            result = subprocess.run(
                [sys.executable, "-m", "scripts.seed_data"],
                capture_output=True, text=True
            )
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print("Seed STDERR:", result.stderr)
        else:
            print(f"Database has {len(cities)} cities - skipping city seed")

        # Check and seed API keys (separate because previous seed might have failed)
        result = await session.execute(select(APIKeyModel))
        keys = result.scalars().all()
        if not keys:
            print("No API keys found - creating test keys...")
            import subprocess
            import sys
            result = subprocess.run(
                [sys.executable, "-m", "scripts.create_keys"],
                capture_output=True, text=True
            )
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print("CreateKeys STDERR:", result.stderr)
        else:
            print(f"Database has {len(keys)} API keys - skipping key creation")

    yield
    # Shutdown
    await close_db()


# Crear aplicación FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    API privada de datos sintéticos de la Generación Z colombiana.

    ## Características
    - Datos sintéticos con distribuciones marginales realistas basadas en estadísticas oficiales del DANE
    - Segmentación por ciudad (Bogotá, Medellín), barrio/comuna/localidad y estrato socioeconómico
    - Autenticación por API key con tiers de acceso (free, pro, enterprise)
    - Rate limiting diferenciado por tier
    - Trazabilidad completa de consultas

    ## Endpoints principales
    - `/metadata`: Metadata del dataset (variables, clasificaciones, fuentes)
    - `/schema`: Esquema de entidades y relaciones
    - `/cities`: Ciudades disponibles con códigos DIVIPOLA
    - `/neighborhoods`: Barrios/comunas/localidades por ciudad
    - `/population/sample`: Muestreo de personas sintéticas con filtros
    - `/aggregate/query`: Consultas de agregación sin exponer microdatos

    ## Autenticación
    Todos los endpoints (excepto `/health`) requieren autenticación vía API key en el header `X-API-Key`.

    ## Nota importante
    Los datos expuestos son SINTÉTICOS. Preservan distribuciones estadísticas basadas en fuentes oficiales
    (DANE, ICFES, MinTIC), pero no representan individuos reales.
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurar rate limiting
app.state.limiter = limiter
app.add_exception_handler(429, rate_limit_exceeded_handler)

# Agregar middleware de autenticación
app.add_middleware(AuthMiddleware)


# Middleware de logging y timing
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Registra cada request con tiempo de procesamiento."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    # Agregar headers de timing
    response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))

    return response


# Incluir routers
app.include_router(health.router)
app.include_router(metadata.router)
app.include_router(cities.router)
app.include_router(neighborhoods.router)
app.include_router(population.router)
app.include_router(aggregate.router)


# Endpoint de schema (esquema de entidades)
@app.get(
    "/schema",
    tags=["Schema"],
    summary="Esquema de entidades y relaciones",
    description="Retorna el esquema de entidades del dataset y sus relaciones.",
)
async def get_schema():
    """
    Retorna el esquema de entidades y relaciones del dataset.

    Incluye:
        - Entidades: cities, neighborhoods, persons, api_keys, subscriptions, query_logs
        - Relaciones entre entidades
        - Tipos de datos y restricciones
    """
    return {
        "entities": {
            "cities": {
                "description": "Ciudades del proyecto con códigos DIVIPOLA oficiales",
                "primary_key": "divipola",
                "fields": {
                    "divipola": {"type": "string(10)", "description": "Código DIVIPOLA oficial"},
                    "name": {"type": "string(100)", "description": "Nombre de la ciudad"},
                    "department": {"type": "string(100)", "description": "Departamento"},
                    "population_total": {"type": "integer", "description": "Población total (proyección DANE)"},
                    "population_genz": {"type": "integer", "description": "Población estimada Gen Z (12-28 años)"},
                },
                "relationships": ["neighborhoods (1:N)", "persons (1:N)"],
            },
            "neighborhoods": {
                "description": "Barrios/comunas/localidades con códigos oficiales",
                "primary_key": "code",
                "fields": {
                    "code": {"type": "string(20)", "description": "Código oficial (DIVIPOLA o código interno)"},
                    "name": {"type": "string(150)", "description": "Nombre del barrio/comuna/localidad"},
                    "city_divipola": {"type": "string(10)", "description": "FK a cities.divipola"},
                    "neighborhood_type": {"type": "string(20)", "description": "Tipo: 'localidad' o 'comuna'"},
                },
                "relationships": ["city (N:1)", "persons (1:N)"],
            },
            "persons": {
                "description": "Personas sintéticas de la Generación Z colombiana",
                "primary_key": "id",
                "fields": {
                    "id": {"type": "string(32)", "description": "ID sintético (hash irreversível)"},
                    "edad": {"type": "integer", "description": "Edad en años (12-28)"},
                    "sexo": {"type": "string(1)", "description": "Sexo (M/F)"},
                    "ciudad_divipola": {"type": "string(10)", "description": "FK a cities.divipola"},
                    "neighborhood_code": {"type": "string(20)", "description": "FK a neighborhoods.code"},
                    "estrato": {"type": "integer", "description": "Estrato socioeconómico (1-6)"},
                    "nivel_educativo": {"type": "string(30)", "description": "Nivel educativo"},
                    "ocupacion": {"type": "string(30)", "description": "Ocupación"},
                    "acceso_internet": {"type": "boolean", "description": "Tiene acceso a internet"},
                    "interes_musical": {"type": "string(30)", "description": "Interés musical"},
                    "interes_tecnologico": {"type": "string(30)", "description": "Interés tecnológico"},
                    "uso_bicicleta": {"type": "string(20)", "description": "Frecuencia de uso de bicicleta"},
                },
                "relationships": ["city (N:1)", "neighborhood (N:1)"],
            },
            "api_keys": {
                "description": "API keys para autenticación",
                "primary_key": "key_hash",
                "fields": {
                    "key_hash": {"type": "string(128)", "description": "Hash bcrypt de la API key"},
                    "key_prefix": {"type": "string(8)", "description": "Primeros 8 caracteres para identificación"},
                    "name": {"type": "string(100)", "description": "Nombre descriptivo de la key"},
                    "tier": {"type": "string(20)", "description": "Tier: free, pro, enterprise"},
                    "is_active": {"type": "boolean", "description": "Si la key está activa"},
                    "created_at": {"type": "datetime", "description": "Fecha de creación"},
                    "last_used_at": {"type": "datetime", "description": "Último uso"},
                },
                "relationships": ["subscription (1:1)", "query_logs (1:N)"],
            },
            "subscriptions": {
                "description": "Suscripciones con tiers y límites de acceso",
                "primary_key": "id",
                "fields": {
                    "id": {"type": "string(32)", "description": "ID de la suscripción"},
                    "api_key_hash": {"type": "string(128)", "description": "FK a api_keys.key_hash"},
                    "tier": {"type": "string(20)", "description": "Tier: free, pro, enterprise"},
                    "queries_per_minute": {"type": "integer", "description": "Límite de queries por minuto"},
                    "queries_per_day": {"type": "integer", "description": "Límite de queries por día"},
                    "max_sample_size": {"type": "integer", "description": "Tamaño máximo de muestra"},
                    "can_download": {"type": "string(1)", "description": "Puede descargar datasets (S/N)"},
                    "started_at": {"type": "datetime", "description": "Inicio de suscripción"},
                    "expires_at": {"type": "datetime", "description": "Vencimiento"},
                },
                "relationships": ["api_key (1:1)"],
            },
            "query_logs": {
                "description": "Logs de consultas para trazabilidad",
                "primary_key": "id",
                "fields": {
                    "id": {"type": "string(32)", "description": "ID del log"},
                    "api_key_hash": {"type": "string(128)", "description": "FK a api_keys.key_hash"},
                    "endpoint": {"type": "string(100)", "description": "Endpoint consultado"},
                    "method": {"type": "string(10)", "description": "Método HTTP"},
                    "query_params": {"type": "text", "description": "Parámetros de la query (JSON)"},
                    "response_status": {"type": "integer", "description": "Código de estado HTTP"},
                    "response_time_ms": {"type": "integer", "description": "Tiempo de respuesta en ms"},
                    "created_at": {"type": "datetime", "description": "Fecha de la consulta"},
                },
                "relationships": ["api_key (N:1)"],
            },
        },
        "relationships_summary": [
            "cities 1:N neighborhoods (una ciudad tiene muchos barrios/comunas)",
            "cities 1:N persons (una ciudad tiene muchas personas)",
            "neighborhoods 1:N persons (un barrio tiene muchas personas)",
            "api_keys 1:1 subscriptions (una key tiene una suscripción)",
            "api_keys 1:N query_logs (una key tiene muchos logs)",
        ],
    }


# Health check adicional con info de BD
@app.get(
    "/health/detailed",
    tags=["Health"],
    summary="Health check detallado",
    description="Verifica el estado de la API y la conexión a la base de datos.",
)
async def health_check_detailed():
    """Health check detallado con verificación de BD."""
    from sqlalchemy import text
    from app.database import async_session

    db_status = "unknown"
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
            db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "service": settings.APP_NAME,
    }
