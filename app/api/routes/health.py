"""
Endpoint de health check.
Público, no requiere autenticación.
"""
from fastapi import APIRouter
from app.config import settings

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    summary="Health check",
    description="Verifica que la API está operativa. Endpoint público.",
    response_description="Estado de salud de la API",
)
async def health_check():
    """
    Verifica el estado de salud de la API.

    Retorna:
        - status: Estado operativo (ok/degraded/down)
        - version: Versión de la API
        - environment: Entorno de ejecución
    """
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "service": settings.APP_NAME,
    }
