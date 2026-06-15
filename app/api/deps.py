from datetime import UTC, datetime

from fastapi import Depends, Request, Security
from fastapi.security import APIKeyHeader, APIKeyQuery, SecurityScopes
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import ProblemError
from app.core.security import digest_api_key, parse_key_prefix, secure_digest_matches
from app.database import get_db
from app.models import ApiClient

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
# A query-param key lets a browser open an authenticated report URL directly.
api_key_query = APIKeyQuery(name="key", auto_error=False)


def _authenticate(
    api_key: str | None,
    required_scopes: list[str],
    request: Request,
    db: Session,
    settings: Settings,
) -> ApiClient:
    if not api_key:
        raise ProblemError(401, "Authentication required", "Provide a valid API key.")
    prefix = parse_key_prefix(api_key)
    if not prefix:
        raise ProblemError(401, "Invalid API key", "The supplied API key is invalid.")
    client = db.scalar(select(ApiClient).where(ApiClient.key_prefix == prefix, ApiClient.active.is_(True)))
    candidate = digest_api_key(api_key, settings.api_key_pepper)
    if client is None or not secure_digest_matches(candidate, client.key_digest):
        raise ProblemError(401, "Invalid API key", "The supplied API key is invalid.")
    missing_scopes = set(required_scopes) - set(client.scopes)
    if missing_scopes:
        raise ProblemError(403, "Insufficient scope", f"Missing required scopes: {sorted(missing_scopes)}")
    quota = request.app.state.quota.consume(client.id, client.requests_per_minute, client.requests_per_day)
    request.state.api_client_id = client.id
    request.state.quota = quota
    # Throttle the write: one update per minute is enough for usage tracking.
    now = datetime.now(UTC)
    last_used = client.last_used_at
    if last_used is not None and last_used.tzinfo is None:
        last_used = last_used.replace(tzinfo=UTC)
    if last_used is None or (now - last_used).total_seconds() > 60:
        client.last_used_at = now
    return client


def get_current_client(
    security_scopes: SecurityScopes,
    request: Request,
    api_key: str | None = Security(api_key_header),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ApiClient:
    return _authenticate(api_key, security_scopes.scopes, request, db, settings)


def get_report_client(
    request: Request,
    header_key: str | None = Security(api_key_header),
    query_key: str | None = Security(api_key_query),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ApiClient:
    return _authenticate(header_key or query_key, ["market:read"], request, db, settings)
