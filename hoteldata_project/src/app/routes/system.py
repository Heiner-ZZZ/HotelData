from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi import Request
from fastapi.templating import Jinja2Templates

from config.redis_settings import get_redis_settings
from src.cache.redis_client import redis_available


router = APIRouter(tags=["system"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


@router.get("/system/redis-status")
def redis_status(request: Request):
    settings = get_redis_settings()
    connected, error = redis_available()
    payload = {
        "enabled": settings.enabled,
        "connected": connected,
        "host": settings.host,
        "port": settings.port,
        "db": settings.db,
        "error": error,
    }
    accept = request.headers.get("accept", "")
    if "text/html" in accept and request.query_params.get("format") != "json":
        return templates.TemplateResponse(
            request,
            "system/redis_status.html",
            {
                "status": payload,
            },
        )
    return payload
