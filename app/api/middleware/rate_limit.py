"""
Middleware de rate limiting por tier de suscripción.
Usa slowapi para limitar requests por minuto según el tier del API key.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request
from starlette.responses import JSONResponse

from app.config import settings


# Crear limiter global
limiter = Limiter(key_func=get_remote_address)


def get_rate_limit_for_tier(tier: str) -> str:
    """Retorna el límite de rate para un tier dado."""
    limits = settings.rate_limits
    return limits.get(tier, limits["free"])


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Handler personalizado para exceso de rate limit."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit excedido.",
            "limit": str(exc.detail),
            "retry_after": exc.retry_after if hasattr(exc, "retry_after") else 60,
        },
    )


def apply_rate_limit(request: Request) -> str:
    """
    Determina el límite de rate basado en el tier del API key.
    Se usa como key function para slowapi.
    """
    if hasattr(request.state, "api_key"):
        tier = request.state.api_key.tier
        return get_rate_limit_for_tier(tier)
    return settings.RATE_LIMIT_FREE
