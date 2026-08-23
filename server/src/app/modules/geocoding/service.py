"""Geocodificación Nominatim (OpenStreetMap) con caché Mongo y rate-limit.

Nominatim es GRATIS pero su política de uso exige: (1) un ``User-Agent``
identificable, (2) máximo 1 petición por segundo, y (3) cachear resultados.
Esta capa cumple las tres y es **best-effort**: ante timeout, error de red o
respuesta vacía devuelve ``None`` y NUNCA bloquea ni rompe el flujo que la
invoca (onboarding / backfill). La caché vive en la colección Mongo
``geocode_cache`` (clave normalizada de la consulta) para no re-consultar
Nominatim por la misma dirección.
"""

from __future__ import annotations

import threading
import time
from typing import Any

from config.settings import get_settings
from src.database.connection import get_database

GEOCODE_CACHE_COLLECTION = "geocode_cache"
# Nominatim pide ≤1 req/s; 1.1s de separación mínima respeta la política.
NOMINATIM_MIN_INTERVAL = 1.1

_last_request_at = 0.0
_rate_lock = threading.Lock()


def _query_key(address: str, city: str, country: str) -> str:
    """Clave normalizada de caché: dirección + ciudad + país en minúsculas."""
    parts = [str(p).strip() for p in (address, city, country) if p and str(p).strip()]
    return " ".join(parts).lower()


def _wait_rate_limit() -> None:
    """Respeta el intervalo mínimo entre peticiones a Nominatim (1 req/s)."""
    global _last_request_at
    with _rate_lock:
        now = time.monotonic()
        wait = NOMINATIM_MIN_INTERVAL - (now - _last_request_at)
        if wait > 0:
            time.sleep(wait)
        _last_request_at = time.monotonic()


def _parse_result(data: Any) -> dict[str, Any] | None:
    """Extrae lat/lng del primer resultado JSON de Nominatim (o ``None``)."""
    if not data or not isinstance(data, list) or not data:
        return None
    first = data[0]
    if not isinstance(first, dict):
        return None
    try:
        return {
            "latitude": float(first["lat"]),
            "longitude": float(first["lon"]),
            "display_name": str(first.get("display_name") or ""),
        }
    except (KeyError, TypeError, ValueError):
        return None


def _cache_get(db: Any, key: str) -> dict[str, Any] | None:
    doc = db[GEOCODE_CACHE_COLLECTION].find_one({"query_key": key}, {"_id": 0})
    if not doc or doc.get("latitude") is None or doc.get("longitude") is None:
        return None
    # Solo el contrato público: los campos internos de la caché
    # (``query_key``/``cached_at``) no se filtran al invocador.
    return {
        "latitude": doc["latitude"],
        "longitude": doc["longitude"],
        "display_name": doc.get("display_name") or "",
    }


def _cache_set(db: Any, key: str, result: dict[str, Any]) -> None:
    db[GEOCODE_CACHE_COLLECTION].replace_one(
        {"query_key": key},
        {"query_key": key, **result, "cached_at": time.time()},
        upsert=True,
    )


def geocode(
    address: str = "",
    *,
    city: str = "",
    country: str = "",
    client: Any = None,
    db: Any = None,
) -> dict[str, Any] | None:
    """Resuelve lat/lng para una dirección/ciudad/país vía Nominatim (cacheado).

    Devuelve ``{"latitude": float, "longitude": float, "display_name": str}``
    o ``None`` si no hay resultado o el servicio falla. ``client`` y ``db`` son
    inyectables para tests; por defecto usa ``httpx`` y ``get_database()``.
    """
    key = _query_key(address, city, country)
    if not key:
        return None
    db = db or get_database()

    cached = _cache_get(db, key)
    if cached is not None:
        return cached

    settings = get_settings()
    query = " ".join(str(p).strip() for p in (address, city, country) if p and str(p).strip())
    headers = {"User-Agent": settings.nominatim_user_agent}
    try:
        _wait_rate_limit()
        if client is not None:
            resp = client.get(
                f"{settings.nominatim_base_url.rstrip('/')}/search",
                params={"format": "json", "q": query, "limit": 1},
                headers=headers,
                timeout=settings.nominatim_timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        else:
            import httpx

            resp = httpx.get(
                f"{settings.nominatim_base_url.rstrip('/')}/search",
                params={"format": "json", "q": query, "limit": 1},
                headers=headers,
                timeout=settings.nominatim_timeout,
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:  # noqa: BLE001 - best-effort: sin red/timeout → None
        return None

    result = _parse_result(data)
    if result is None:
        return None
    _cache_set(db, key, result)
    return result
