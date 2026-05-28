from __future__ import annotations

from typing import Any

from config.redis_settings import get_redis_settings


def get_redis_client() -> Any | None:
    settings = get_redis_settings()
    if not settings.enabled:
        return None
    try:
        import redis
    except ImportError as exc:
        raise RuntimeError("Redis esta habilitado, pero el paquete redis no esta instalado.") from exc
    return redis.Redis.from_url(settings.url, decode_responses=True)


def cache_available() -> bool:
    client = get_redis_client()
    if client is None:
        return False
    try:
        return bool(client.ping())
    except Exception:
        return False
