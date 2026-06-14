import uuid

from sqlalchemy import select, text

from app.core.config import get_settings
from app.core.rate_limit import RedisQuota
from app.database import SessionLocal
from app.models import ApiClient


def main() -> None:
    settings = get_settings()
    if not settings.database_url.startswith(("postgresql://", "postgresql+psycopg://")):
        raise RuntimeError("Integration check requires PostgreSQL")
    if not settings.redis_url:
        raise RuntimeError("Integration check requires Redis")
    with SessionLocal.begin() as db:
        assert db.scalar(select(1)) == 1
        db.execute(text("SELECT pg_advisory_xact_lock(20260613)"))
        client = ApiClient(
            name="ci-integration",
            key_prefix=uuid.uuid4().hex[:12],
            key_digest=uuid.uuid4().hex + uuid.uuid4().hex,
            tier="free",
            scopes=["aggregate:read"],
            requests_per_minute=5,
            requests_per_day=10,
            max_sample_size=10,
        )
        db.add(client)
    quota = RedisQuota(settings.redis_url)
    result = quota.consume(f"ci:{uuid.uuid4()}", 5, 10)
    assert result.minute_remaining == 4
    assert quota.ping()
    print("PostgreSQL and Redis integration check passed")


if __name__ == "__main__":
    main()
