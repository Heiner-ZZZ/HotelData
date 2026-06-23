from fastapi import APIRouter
from fastapi import Request

from config.redis_settings import get_redis_settings
from src.cache.redis_client import redis_available


router = APIRouter(tags=["system"])


@router.get("/system/redis-status")
def redis_status(request: Request):
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
