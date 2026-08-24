"""Rutas estratégicas TAF14 — Vista A (hotel individual) y Vista B (cartera).

Los 7 informes dictados en TAF14: Vista A = IE-H01 (desempeño + rentabilidad
por plan) e IE-H02 (posicionamiento); Vista B = IE-G01 (KPIs estratégicos),
IE-G02 (rankings R-G01..R-G06), IE-G03 (rentabilidad de cartera), IE-G04
(mercados) e IE-G05 (forecasting). Prefijo ``/api/strategic/*``.

Gates por vista (permisos granulares, separados por diseño): Vista A
(``/hotel/{prop_id}``) exige ``reports.strategic.read`` (lo tiene el dueño de
hotel); Vista B (``/portfolio`` y ``/markets``) exige
``reports.strategic.portfolio.read`` (exclusivo de dirección). Antes ambos
compartían un único permiso, lo que hacía que el botón de SISTEMA apareciera
para el gerente de hotel pero la ruta lo rechazara ("no me abren"). Respuesta
tipada con modelos Pydantic ``*Response``
(``src/app/modules/strategic/schemas.py``).

Scoping (deny-by-default, patrón hotel_filter): la Vista A exige pertenencia
del hotel (``user_can_access_hotel`` → 404 fuera de alcance) y el drill-down
de la cartera (``portfolio?prop_id=``) aplica el mismo check. Roles no
filtrados (super_admin/admin_sistema) conservan la cartera completa.

Contrato de disponibilidad: rango invertido → 400; ClickHouse caído →
``available: false`` con ``message`` (nunca 500). Lee SOLO las tablas
``strat_*`` de ClickHouse.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status

from src.app.modules.strategic.kpi_strategic import (
    get_hotel_dashboard,
    get_markets_dashboard,
    get_portfolio_dashboard,
)
from src.app.modules.strategic.schemas import (
    StrategicHotelResponse,
    StrategicMarketsResponse,
    StrategicPortfolioResponse,
)
from src.app.security.dependencies import require_permission
from src.app.security.hotel_filter import user_can_access_hotel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/strategic", tags=["strategic"])

VISTA_A_GATE = require_permission("reports.strategic.read")
VISTA_B_GATE = require_permission("reports.strategic.portfolio.read")


def _require_hotel_in_scope(current_user: dict, prop_id: int) -> None:
    """Vista A / drill-down: solo los hoteles asignados (deny-by-default).

    Fuera de alcance → 404 (no se filtra la existencia del hotel). Roles no
    filtrados (super_admin/admin_sistema) siempre en alcance.
    """
    if not user_can_access_hotel(current_user, prop_id):
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Informe no disponible para el hotel {prop_id}.",
        )


def _dashboard_or_400(
    fn: Callable[..., dict[str, Any]],
    **params: Any,
) -> dict[str, Any]:
    """Ejecuta el dashboard y traduce un rango inválido a HTTP 400."""
    try:
        return fn(**params)
    except ValueError as exc:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/portfolio", response_model=StrategicPortfolioResponse)
def portfolio_dashboard_api(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    days: int = Query(default=30, ge=30, le=730),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=5, ge=5, le=100),
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(VISTA_B_GATE),
) -> StrategicPortfolioResponse:
    """Vista B — KPIs estratégicos + rankings + rentabilidad de cartera
    (IE-G01/G02/G03). ``prop_id`` hace drill-down a un hotel de la cartera
    (scoped: 404 fuera de alcance)."""
    if prop_id is not None:
        _require_hotel_in_scope(current_user, prop_id)
    result = _dashboard_or_400(
        get_portfolio_dashboard,
        date_from=date_from,
        date_to=date_to,
        days=days,
        page=page,
        page_size=page_size,
        prop_id=prop_id,
    )
    return StrategicPortfolioResponse.model_validate(result)


@router.get("/hotel/{prop_id}", response_model=StrategicHotelResponse)
def hotel_dashboard_api(
    prop_id: int,
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    days: int = Query(default=30, ge=30, le=730),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=5, ge=5, le=100),
    planes_page: int = Query(default=1, ge=1, alias="ppage"),
    current_user: dict = Depends(VISTA_A_GATE),
) -> StrategicHotelResponse:
    """Vista A — dashboard de UN hotel (IE-H01/H02): KPIs + serie + tabla de
    registros (``page``) + rentabilidad por plan (``ppage``) + posicionamiento.
    Exige pertenencia (``assigned_hotels``, deny-by-default)."""
    _require_hotel_in_scope(current_user, prop_id)
    result = _dashboard_or_400(
        get_hotel_dashboard,
        prop_id=prop_id,
        date_from=date_from,
        date_to=date_to,
        days=days,
        page=page,
        page_size=page_size,
        planes_page=planes_page,
    )
    return StrategicHotelResponse.model_validate(result)


@router.get("/markets", response_model=StrategicMarketsResponse)
def markets_dashboard_api(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    days: int = Query(default=30, ge=30, le=730),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=5, ge=5, le=100),
    current_user: dict = Depends(VISTA_B_GATE),
) -> StrategicMarketsResponse:
    """Vista B — mapa de mercados (IE-G04): matriz crecimiento × posición."""
    result = _dashboard_or_400(
        get_markets_dashboard,
        date_from=date_from,
        date_to=date_to,
        days=days,
        page=page,
        page_size=page_size,
    )
    return StrategicMarketsResponse.model_validate(result)
