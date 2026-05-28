from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class RedisSettings:
    enabled: bool
    url: str
    default_ttl_seconds: int


def get_redis_settings() -> RedisSettings:
    return RedisSettings(
        enabled=os.getenv("REDIS_ENABLED", "false").lower() == "true",
        url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        default_ttl_seconds=int(os.getenv("REDIS_DEFAULT_TTL_SECONDS", "300")),
    )
