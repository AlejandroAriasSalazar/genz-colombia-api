from datetime import UTC, datetime

from fastapi import Depends, Request, Security
from fastapi.security import APIKeyHeader, SecurityScopes
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import ProblemError
from app.core.security import digest_api_key, parse_key_prefix, secure_digest_matches
from app.database import get_db
from app.models import ApiClient

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_current_client(
    security_scopes: SecurityScopes,
    request: Request,
    api_key: str | None = Security(api_key_header),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ApiClient:
    if not api_key:
        raise ProblemError(401, "Authentication required", "Provide a valid X-API-Key header.")
    prefix = parse_key_prefix(api_key)
    if not prefix:
        raise ProblemError(401, "Invalid API key", "The supplied API key is invalid.")
    client = db.scalar(select(ApiClient).where(ApiClient.key_prefix == prefix, ApiClient.active.is_(True)))
    candidate = digest_api_key(api_key, settings.api_key_pepper)
    if client is None or not secure_digest_matches(candidate, client.key_digest):
        raise ProblemError(401, "Invalid API key", "The supplied API key is invalid.")
    missing_scopes = set(security_scopes.scopes) - set(client.scopes)
    if missing_scopes:
        raise ProblemError(403, "Insufficient scope", f"Missing required scopes: {sorted(missing_scopes)}")
    quota = request.app.state.quota.consume(client.id, client.requests_per_minute, client.requests_per_day)
    request.state.api_client_id = client.id
    request.state.quota = quota
    client.last_used_at = datetime.now(UTC)
    return client
