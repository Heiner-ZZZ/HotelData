from __future__ import annotations

from fastapi import APIRouter

from config.redis_settings import get_redis_settings
from src.cache.redis_client import redis_available


router = APIRouter(tags=["system"])


@router.get("/system/redis-status")
def redis_status() -> dict[str, object]:
    settings = get_redis_settings()
    connected, error = redis_available()
    return {
        "enabled": settings.enabled,
        "connected": connected,
        "host": settings.host,
        "port": settings.port,
        "db": settings.db,
        "error": error,
    }
