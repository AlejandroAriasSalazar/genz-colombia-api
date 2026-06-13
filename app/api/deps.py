"""
Dependencias de la API: autenticación, rate limiting, trazabilidad.
"""
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import bcrypt
from datetime import datetime
import uuid

from app.database import get_db
from app.models.api_key import APIKey
from app.models.query_log import QueryLog


# Esquema de seguridad para API Key
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _truncate_key(key: str) -> bytes:
    """Trunca la clave a 72 bytes (límite de bcrypt)."""
    return key.encode('utf-8')[:72]


def hash_api_key(key: str) -> str:
    """Hashea una API key para almacenamiento seguro."""
    return bcrypt.hashpw(_truncate_key(key), bcrypt.gensalt()).decode('utf-8')


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Verifica una API key contra su hash."""
    try:
        return bcrypt.checkpw(_truncate_key(plain_key), hashed_key.encode('utf-8'))
    except Exception:
        return False


async def get_current_api_key(
    request: Request,
    api_key: str = Depends(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> APIKey:
    """
    Valida la API key del header y retorna el objeto APIKey.
    Lanza 401 si la key es inválida o inactiva.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key requerida. Incluye el header X-API-Key.",
        )

    # Buscar todas las keys activas
    result = await db.execute(select(APIKey).where(APIKey.is_active == True))
    all_keys = result.scalars().all()

    # Verificar cuál key coincide
    matched_key = None
    for key_obj in all_keys:
        if verify_api_key(api_key, key_obj.key_hash):
            matched_key = key_obj
            break

    if not matched_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida o inactiva.",
        )

    # Actualizar last_used_at
    matched_key.last_used_at = datetime.utcnow()
    await db.commit()

    # Guardar en request state para trazabilidad
    request.state.api_key = matched_key
    request.state.query_id = str(uuid.uuid4())

    return matched_key


async def log_query(
    request: Request,
    response_status: int,
    response_time_ms: int,
    db: AsyncSession = Depends(get_db),
):
    """Registra la consulta en query_logs para trazabilidad."""
    if not hasattr(request.state, "api_key"):
        return

    query_log = QueryLog(
        id=str(uuid.uuid4()),
        api_key_hash=request.state.api_key.key_hash,
        endpoint=request.url.path,
        method=request.method,
        query_params=str(dict(request.query_params)),
        response_status=response_status,
        response_time_ms=response_time_ms,
    )
    db.add(query_log)
    await db.commit()
