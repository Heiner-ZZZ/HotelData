"""Analytics routes — ClickHouse health checks.

Mirrors the ``/system/redis-status`` pattern: always returns 200 with a
``connected`` boolean, plus diagnostic fields. Never raises on a down
ClickHouse — the endpoint reports ``connected: false`` with the error
string instead, so monitoring can distinguish "unreachable" from
"endpoint broken".
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status

from config.settings import get_settings
from src.app.modules.analytics.kpi_reports import (
    get_booking_dashboard,
    get_booking_nights_dashboard,
    get_funnel_dashboard,
    get_funnel_property_channel_dashboard,
    get_inventory_dashboard,
    get_rate_dashboard,
)
from src.app.security.dependencies import require_any_permission

logger = logging.getLogger(__name__)

try:
    import clickhouse_connect
except Exception:  # pragma: no cover - optional dependency fallback
    clickhouse_connect = None  # type: ignore[assignment]


router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# Informes compuestos TA12: accesibles para quien tenga reports.read (admin) o
# revenue.read (gerente de hotel / tarifas).
_KPI_REPORT_PERMISSION = require_any_permission("reports.read", "revenue.read")


def _dashboard_or_400(
    fn: Callable[..., dict[str, Any]],
    **params: Any,
) -> dict[str, Any]:
    """Ejecuta el dashboard y traduce un rango inválido a HTTP 400."""
    try:
        return fn(**params)
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

# Short timeouts so a down ClickHouse fails fast instead of hanging the
# request (urllib3 retries back off otherwise).
_CONNECT_TIMEOUT_SECONDS = 3
_SEND_RECEIVE_TIMEOUT_SECONDS = 3


# ─── Informes compuestos KPI (ClickHouse) ────────────────────────────────


@router.get("/booking")
def booking_dashboard_api(
    prop_id: int | None = Query(default=None, ge=1),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(_KPI_REPORT_PERMISSION),
):
    """Informe compuesto de reservas sobre ``kpi_booking_daily`` (ClickHouse)."""
    return _dashboard_or_400(
        get_booking_dashboard,
        prop_id=prop_id,
        date_from=date_from,
        date_to=date_to,
        days=days,
        page=page,
        page_size=page_size,
    )


@router.get("/booking-nights")
def booking_nights_dashboard_api(
    prop_id: int | None = Query(default=None, ge=1),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(_KPI_REPORT_PERMISSION),
):
    """Informe de ocupación por noche sobre ``kpi_booking_nights_daily``."""
    return _dashboard_or_400(
        get_booking_nights_dashboard,
        prop_id=prop_id,
        date_from=date_from,
        date_to=date_to,
        days=days,
        page=page,
        page_size=page_size,
    )


@router.get("/rate")
def rate_dashboard_api(
    prop_id: int | None = Query(default=None, ge=1),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(_KPI_REPORT_PERMISSION),
):
    """Informe de tarifa publicada sobre ``kpi_rate_daily`` (ClickHouse)."""
    return _dashboard_or_400(
        get_rate_dashboard,
        prop_id=prop_id,
        date_from=date_from,
        date_to=date_to,
        days=days,
        page=page,
        page_size=page_size,
    )


@router.get("/inventory")
def inventory_dashboard_api(
    prop_id: int | None = Query(default=None, ge=1),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(_KPI_REPORT_PERMISSION),
):
    """Informe de disponibilidad sobre ``kpi_inventory_daily`` (ClickHouse)."""
    return _dashboard_or_400(
        get_inventory_dashboard,
        prop_id=prop_id,
        date_from=date_from,
        date_to=date_to,
        days=days,
        page=page,
        page_size=page_size,
    )


@router.get("/funnel")
def funnel_dashboard_api(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(_KPI_REPORT_PERMISSION),
):
    """Informe global de embudo sobre ``kpi_funnel_daily`` (sin prop_id)."""
    return _dashboard_or_400(
        get_funnel_dashboard,
        prop_id=None,
        date_from=date_from,
        date_to=date_to,
        days=days,
        page=page,
        page_size=page_size,
    )


@router.get("/funnel-property-channel")
def funnel_property_channel_dashboard_api(
    prop_id: int | None = Query(default=None, ge=1),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(_KPI_REPORT_PERMISSION),
):
    """Informe de embudo por hotel/canal sobre ``kpi_funnel_property_channel_daily``."""
    return _dashboard_or_400(
        get_funnel_property_channel_dashboard,
        prop_id=prop_id,
        date_from=date_from,
        date_to=date_to,
        days=days,
        page=page,
        page_size=page_size,
    )


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
