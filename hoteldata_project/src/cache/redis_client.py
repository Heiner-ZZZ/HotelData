from __future__ import annotations

from typing import Any

from config.redis_settings import RedisSettings, get_redis_settings

try:
    import redis
    from redis import Redis
except Exception:  # pragma: no cover - optional dependency fallback
    redis = None
    Redis = Any  # type: ignore[assignment]


def get_redis_client(settings: RedisSettings | None = None) -> Redis | None:
    settings = settings or get_redis_settings()
    if not settings.enabled or redis is None:
        return None
    return redis.Redis.from_url(
        settings.url,
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )


def redis_available() -> tuple[bool, str | None]:
    settings = get_redis_settings()
    if not settings.enabled:
        return False, "Redis disabled by configuration."
    if redis is None:
        return False, "Python package 'redis' is not installed."

    client = get_redis_client(settings)
    if client is None:
        return False, "Redis client could not be initialized."

    try:
        client.ping()
        return True, None
    except Exception as exc:  # pragma: no cover - depends on local service state
        return False, str(exc)
