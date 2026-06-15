import hashlib
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from starlette.background import BackgroundTask

from app.api.routes import catalog, enrichment, health, market, population, reports
from app.core.config import Settings, get_settings
from app.core.errors import install_error_handlers, problem_response
from app.core.rate_limit import build_quota_backend
from app.database import SessionLocal
from app.models import QueryLog

logger = logging.getLogger("genz_api_v3")

# Health/preflight traffic is high-volume and low-signal; keep it out of the audit log.
_SKIP_LOG_PREFIXES = ("/api/v3/health",)


def _resolve_client_ip(request: Request, settings: Settings) -> str | None:
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _write_query_log(data: dict) -> None:
    try:
        with SessionLocal.begin() as db:
            db.add(QueryLog(**data))
    except SQLAlchemyError:
        logger.exception("query_log_write_failed", extra={"request_id": data.get("request_id")})


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.raw_storage_path.mkdir(parents=True, exist_ok=True)
    app.state.quota = build_quota_backend(settings)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    # Endurecimiento: en producción no se expone la documentación interactiva ni el
    # esquema OpenAPI (reduce el mapeo de la superficie de la API). En desarrollo/test
    # siguen disponibles en /docs, /redoc y /openapi.json.
    expose_docs = settings.environment != "production"
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "API versionada de población sintética Gen Z. Las personas se generan de forma "
            "reproducible a partir de agregados oficiales DANE; nunca representan individuos reales."
        ),
        docs_url="/docs" if expose_docs else None,
        redoc_url="/redoc" if expose_docs else None,
        openapi_url="/openapi.json" if expose_docs else None,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key", "X-Request-ID"],
        expose_headers=[
            "X-Request-ID",
            "X-Process-Time-Ms",
            "X-RateLimit-Minute-Remaining",
            "X-RateLimit-Day-Remaining",
        ],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        started = time.perf_counter()
        supplied_request_id = request.headers.get("X-Request-ID")
        try:
            request_id = str(uuid.UUID(supplied_request_id)) if supplied_request_id else str(uuid.uuid4())
        except ValueError:
            return problem_response(request, 400, "Invalid request ID", "X-Request-ID must be a UUID.")
        request.state.request_id = request_id
        response = await call_next(request)
        duration_ms = max(0, round((time.perf_counter() - started) * 1000))
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = str(duration_ms)
        # Baseline security headers. Referrer-Policy is critical: the report page can
        # carry an API key in its URL, and no-referrer stops it leaking to the CDN.
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        quota = getattr(request.state, "quota", None)
        if quota:
            response.headers["X-RateLimit-Minute-Remaining"] = str(quota.minute_remaining)
            response.headers["X-RateLimit-Day-Remaining"] = str(quota.day_remaining)
        should_log = request.method != "OPTIONS" and not request.url.path.startswith(_SKIP_LOG_PREFIXES)
        if should_log:
            client_ip = _resolve_client_ip(request, settings)
            log_data = {
                "request_id": request_id,
                "api_client_id": getattr(request.state, "api_client_id", None),
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_ip_hash": (
                    hashlib.sha256(client_ip.encode()).hexdigest() if client_ip else None
                ),
            }
            # Persist after the response is flushed so the client is never blocked on the write.
            response.background = BackgroundTask(_write_query_log, log_data)
        return response

    install_error_handlers(app)
    app.include_router(health.router, prefix="/api/v3")
    app.include_router(catalog.router, prefix="/api/v3")
    app.include_router(population.router, prefix="/api/v3")
    app.include_router(market.router, prefix="/api/v3")
    app.include_router(reports.router, prefix="/api/v3")
    app.include_router(enrichment.router, prefix="/api/v3")

    @app.get("/", include_in_schema=False)
    def root():
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "api_base": "/api/v3",
        }

    return app


app = create_app()
