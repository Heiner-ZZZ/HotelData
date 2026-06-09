from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class RedisSettings:
    enabled: bool
    host: str
    port: int
    db: int
    url: str
    default_ttl_seconds: int


def get_redis_settings() -> RedisSettings:
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    db = int(os.getenv("REDIS_DB", "0"))
    default_url = f"redis://{host}:{port}/{db}"
    url = os.getenv("REDIS_URL", default_url)
    parsed = urlparse(url)
    parsed_host = parsed.hostname or host
    parsed_port = parsed.port or port
    parsed_db = db
    parsed_path = (parsed.path or "").lstrip("/")
    if parsed_path.isdigit():
        parsed_db = int(parsed_path)

    return RedisSettings(
        enabled=os.getenv("REDIS_ENABLED", "false").lower() == "true",
        host=parsed_host,
        port=parsed_port,
        db=parsed_db,
        url=url,
        default_ttl_seconds=int(os.getenv("REDIS_DEFAULT_TTL_SECONDS", "300")),
    )
