import hashlib
import hmac
import secrets

KEY_PREFIX = "gzv3"


def digest_api_key(api_key: str, pepper: str) -> str:
    return hmac.new(pepper.encode(), api_key.encode(), hashlib.sha256).hexdigest()


def generate_api_key() -> tuple[str, str]:
    public_prefix = secrets.token_hex(6)
    secret = secrets.token_urlsafe(32)
    return f"{KEY_PREFIX}_{public_prefix}_{secret}", public_prefix


def parse_key_prefix(api_key: str) -> str | None:
    parts = api_key.split("_", 2)
    if len(parts) != 3 or parts[0] != KEY_PREFIX:
        return None
    return parts[1]


def secure_digest_matches(candidate: str, expected: str) -> bool:
    return hmac.compare_digest(candidate, expected)


def stable_hmac_hex(secret: str, value: str, length: int = 32) -> str:
    return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()[:length]
