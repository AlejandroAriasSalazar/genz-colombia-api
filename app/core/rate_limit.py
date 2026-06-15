import threading
import time
from dataclasses import dataclass

from app.core.config import Settings
from app.core.errors import ProblemError

try:
    import redis
except ImportError:  # pragma: no cover - Redis is installed in production image
    redis = None


@dataclass
class QuotaResult:
    minute_remaining: int
    day_remaining: int


class InMemoryQuota:
    def __init__(self) -> None:
        self._values: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()

    def _increment(self, key: str, ttl: int) -> int:
        now = time.time()
        value, expires = self._values.get(key, (0, now + ttl))
        if expires <= now:
            value, expires = 0, now + ttl
        value += 1
        self._values[key] = (value, expires)
        return value

    def consume(self, client_id: str, per_minute: int, per_day: int) -> QuotaResult:
        now = int(time.time())
        minute_key = f"{client_id}:m:{now // 60}"
        day_key = f"{client_id}:d:{now // 86400}"
        with self._lock:
            minute = self._increment(minute_key, 120)
            day = self._increment(day_key, 172800)
        if minute > per_minute or day > per_day:
            raise ProblemError(429, "Quota exceeded", "The API quota for this client has been exceeded.")
        return QuotaResult(per_minute - minute, per_day - day)

    def ping(self) -> bool:
        return True


class RedisQuota:
    SCRIPT = """
    local minute = redis.call('INCR', KEYS[1])
    if minute == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
    local day = redis.call('INCR', KEYS[2])
    if day == 1 then redis.call('EXPIRE', KEYS[2], ARGV[2]) end
    return {minute, day}
    """

    def __init__(self, url: str) -> None:
        if redis is None:
            raise RuntimeError("redis package is required")
        self.client = redis.Redis.from_url(url, decode_responses=True)

    def consume(self, client_id: str, per_minute: int, per_day: int) -> QuotaResult:
        now = int(time.time())
        values = self.client.eval(
            self.SCRIPT,
            2,
            f"genz:v3:quota:{client_id}:m:{now // 60}",
            f"genz:v3:quota:{client_id}:d:{now // 86400}",
            120,
            172800,
        )
        minute, day = int(values[0]), int(values[1])
        if minute > per_minute or day > per_day:
            raise ProblemError(429, "Quota exceeded", "The API quota for this client has been exceeded.")
        return QuotaResult(per_minute - minute, per_day - day)

    def ping(self) -> bool:
        return bool(self.client.ping())


def build_quota_backend(settings: Settings):
    if settings.redis_url:
        return RedisQuota(settings.redis_url)
    return InMemoryQuota()
