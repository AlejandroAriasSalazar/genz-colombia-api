"""
Middleware de autenticación por API key.
Se aplica a todos los endpoints excepto /health.
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time

from app.api.deps import get_current_api_key
from app.database import async_session


# Endpoints que no requieren autenticación
PUBLIC_ENDPOINTS = ["/health", "/health/detailed", "/docs", "/openapi.json", "/redoc"]


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware que valida API key en cada request."""

    async def dispatch(self, request: Request, call_next):
        # Skip auth para endpoints públicos
        if request.url.path in PUBLIC_ENDPOINTS:
            return await call_next(request)

        # Skip OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        start_time = time.time()

        # Validar API key
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return Response(
                content='{"detail": "API key requerida. Incluye el header X-API-Key."}',
                status_code=401,
                media_type="application/json",
            )

        # Verificar key contra BD
        async with async_session() as db:
            try:
                await get_current_api_key(request, api_key, db)
            except HTTPException as e:
                return Response(
                    content=f'{{"detail": "{e.detail}"}}',
                    status_code=e.status_code,
                    media_type="application/json",
                )

        response = await call_next(request)

        # Log query
        process_time = time.time() - start_time
        async with async_session() as db:
            try:
                from app.api.deps import log_query
                await log_query(request, response.status_code, int(process_time * 1000), db)
            except Exception:
                pass  # No fallar si el logging falla

        return response
