import hashlib
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes import catalog, health, population
from app.core.config import get_settings
from app.core.errors import install_error_handlers, problem_response
from app.core.rate_limit import build_quota_backend
from app.database import SessionLocal
from app.models import QueryLog

logger = logging.getLogger("genz_api_v2")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.raw_storage_path.mkdir(parents=True, exist_ok=True)
    app.state.quota = build_quota_backend(settings)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "API versionada de población sintética Gen Z. Las personas se generan de forma "
            "reproducible a partir de agregados oficiales DANE; nunca representan individuos reales."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
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
        quota = getattr(request.state, "quota", None)
        if quota:
            response.headers["X-RateLimit-Minute-Remaining"] = str(quota.minute_remaining)
            response.headers["X-RateLimit-Day-Remaining"] = str(quota.day_remaining)
        try:
            with SessionLocal.begin() as db:
                client_ip = request.client.host if request.client else None
                db.add(
                    QueryLog(
                        request_id=request_id,
                        api_client_id=getattr(request.state, "api_client_id", None),
                        method=request.method,
                        path=request.url.path,
                        status_code=response.status_code,
                        duration_ms=duration_ms,
                        client_ip_hash=(
                            hashlib.sha256(client_ip.encode()).hexdigest() if client_ip else None
                        ),
                    )
                )
        except SQLAlchemyError:
            logger.exception("query_log_write_failed", extra={"request_id": request_id})
        return response

    install_error_handlers(app)
    app.include_router(health.router, prefix="/api/v2")
    app.include_router(catalog.router, prefix="/api/v2")
    app.include_router(population.router, prefix="/api/v2")

    @app.get("/", include_in_schema=False)
    def root():
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "api_base": "/api/v2",
        }

    return app


app = create_app()
