from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.app.features.collections.service import collection_counts
from src.app.features.dashboard.service import dashboard_overview
from src.app.features.quality.service import quality_summary
from src.database.connection import get_database


logger = logging.getLogger(__name__)
CACHE_COLLECTION = "kpi_summary"
CACHE_ID = "dashboard_kpis"


def _build_kpi_payload() -> dict:
    return {
        "quality": quality_summary(),
        "overview": dashboard_overview(),
        "counts": collection_counts(),
    }


def refresh_kpis() -> dict:
    db = get_database()
    payload = _build_kpi_payload()
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "_id": CACHE_ID,
        "updated_at": now,
        "payload": payload,
    }
    db[CACHE_COLLECTION].replace_one({"_id": CACHE_ID}, doc, upsert=True)
    return {
        "cached_at": now,
        "payload": payload,
        "ok": True,
        "display_message": "KPIs recalculados y cacheados correctamente.",
    }


def refresh_kpis_background() -> None:
    try:
        refresh_kpis()
        logger.info("KPI cache refreshed successfully on startup.")
    except Exception:
        logger.exception("Failed to refresh KPI cache on startup.")


def get_kpis() -> dict:
    db = get_database()
    doc = db[CACHE_COLLECTION].find_one({"_id": CACHE_ID})
    
    should_refresh = False
    if doc is None:
        should_refresh = True
    else:
        try:
            updated_at_str = doc.get("updated_at", "")
            updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - updated_at).total_seconds()
            if age > 30:
                should_refresh = True
        except Exception:
            should_refresh = True
            
    if should_refresh:
        try:
            return refresh_kpis()
        except Exception:
            logger.exception("Failed to auto-refresh KPIs")
            if doc is not None:
                return {
                    "cached_at": doc.get("updated_at", ""),
                    "payload": doc.get("payload", {}),
                }
            raise

    return {
        "cached_at": doc.get("updated_at", ""),
        "payload": doc.get("payload", {}),
    }

