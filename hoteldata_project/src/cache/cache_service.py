from __future__ import annotations

import json
from typing import Any

from config.redis_settings import get_redis_settings
from src.cache.redis_client import get_redis_client


def set_cache(key: str, value: Any, ttl_seconds: int | None = None) -> bool:
    settings = get_redis_settings()
    client = get_redis_client(settings)
    if client is None:
        return False

    try:
        payload = json.dumps(value, ensure_ascii=True, default=str)
        client.setex(key, ttl_seconds or settings.default_ttl_seconds, payload)
        return True
    except Exception:
        return False


def get_cache(key: str) -> Any | None:
    client = get_redis_client()
    if client is None:
        return None

    try:
        payload = client.get(key)
        if payload is None:
            return None
        return json.loads(payload)
    except Exception:
        return None


def delete_cache(key: str) -> bool:
    client = get_redis_client()
    if client is None:
        return False

    try:
        client.delete(key)
        return True
    except Exception:
        return False
