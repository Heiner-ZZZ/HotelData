"""Analytics routes — ClickHouse health checks.

Mirrors the ``/system/redis-status`` pattern: always returns 200 with a
``connected`` boolean, plus diagnostic fields. Never raises on a down
ClickHouse — the endpoint reports ``connected: false`` with the error
string instead, so monitoring can distinguish "unreachable" from
"endpoint broken".
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

from config.settings import get_settings

logger = logging.getLogger(__name__)

try:
    import clickhouse_connect
except Exception:  # pragma: no cover - optional dependency fallback
    clickhouse_connect = None  # type: ignore[assignment]


router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# Short timeouts so a down ClickHouse fails fast instead of hanging the
# request (urllib3 retries back off otherwise).
_CONNECT_TIMEOUT_SECONDS = 3
_SEND_RECEIVE_TIMEOUT_SECONDS = 3


@router.get("/health")
def analytics_health() -> dict[str, Any]:
    """Probe ClickHouse connectivity and report service state.

    Returns a 200 with ``connected`` reflecting the real state:

    ```json
    {
      "connected": true,
      "host": "clickhouse",
      "port": 8123,
      "database": "hoteldata",
      "user": "default",
      "version": "26.7.1.1315",
      "error": null
    }
    ```
    """
    settings = get_settings()
    result: dict[str, Any] = {
        "connected": False,
        "host": settings.clickhouse_host,
        "port": settings.clickhouse_port,
        "database": settings.clickhouse_database,
        "user": settings.clickhouse_user,
        "version": None,
        "error": None,
    }

    if clickhouse_connect is None:
        result["error"] = "Python package 'clickhouse-connect' is not installed."
        return result

    client = None
    try:
        # NOTE: get_client() is eager — it performs the initial round-trip
        # (SELECT version(), timezone()) during construction and raises
        # OperationalError on an unreachable server. The try/except below is
        # therefore the real connectivity guard; there is no separate ping
        # needed (that round-trip would be redundant).
        client = clickhouse_connect.get_client(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            username=settings.clickhouse_user,
            password=settings.clickhouse_password,
            database=settings.clickhouse_database,
            connect_timeout=_CONNECT_TIMEOUT_SECONDS,
            send_receive_timeout=_SEND_RECEIVE_TIMEOUT_SECONDS,
        )
        rows = client.query("SELECT version()").result_rows
        if rows:
            result["version"] = str(rows[0][0])
        result["connected"] = True
        return result
    except Exception as exc:  # pragma: no cover - depends on local service state
        logger.warning("analytics.health.clickhouse_down: %s", exc)
        result["error"] = str(exc)
        return result
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:  # pragma: no cover
                pass
