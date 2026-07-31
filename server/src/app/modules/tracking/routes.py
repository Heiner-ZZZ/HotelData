"""Tracking routes — lightweight analytics for user interactions."""

from __future__ import annotations

import logging
from fastapi import APIRouter, Body, Request

logger = logging.getLogger(__name__)
from datetime import datetime, timezone

from src.database.connection import get_database

tracking_api_router = APIRouter(prefix="/api/tracking", tags=["tracking-api"])


ALLOWED_SOURCES = {"search", "detail", "compare"}


# Lazy index creation: only runs once on the first request.
_tracking_indexes_ready = False


def ensure_tracking_indexes() -> None:
    global _tracking_indexes_ready
    if _tracking_indexes_ready:
        return
    db = get_database()
    db.click_events.create_index(
        [("prop_id", 1), ("clicked_at", -1)],
        name="idx_click_events_prop_clicked",
    )
    _tracking_indexes_ready = True


@tracking_api_router.post("/hotel-click")
def track_hotel_click(
    request: Request,
    payload: dict = Body(...),
):
    """Track a click on a hotel detail page from search results or other sources.

    Public endpoint: clicks are tracked for both authenticated and anonymous users.
    """
    ensure_tracking_indexes()
    db = get_database()
    raw_prop_id = payload.get("prop_id")
    source = payload.get("source", "search")

    # Defensive coercion: stale or buggy clients may send `null`, `""`,
    # or `prop_id <= 0` from seed-data sentinels. We used to raise 400
    # here, but that flooded the browser console with 400 Bad Request
    # errors on every page interaction for guests using older bundles.
    # Gracefully ignore — tracking must NEVER block UX. Logged at WARNING
    # so operating dashboards can flag a flood of stale clients (a bot
    # farming an old bundle would surface in minutes, not weeks).
    def _ignore(reason: str, raw) -> dict:
        sid = request.cookies.get("session_id") or request.headers.get("x-session-id") or ""
        logger.warning(
            "tracking.hotel-click.ignored",
            extra={"reason": reason, "raw": raw, "session_id": sid[:8]},
        )
        return {"ok": True, "ignored": True, "reason": reason}

    try:
        prop_id = int(raw_prop_id)
    except (TypeError, ValueError):
        return _ignore("invalid_prop_id", raw_prop_id)

    if prop_id <= 0:
        return _ignore("non_positive_prop_id", raw_prop_id)

    if source not in ALLOWED_SOURCES:
        return _ignore("invalid_source", source)

    current_user = getattr(request.state, "current_user", None) or {}
    user_id = current_user.get("user_id") or current_user.get("sub")

    db.click_events.insert_one({
        "prop_id": int(prop_id),
        "source": source,
        "user_id": user_id if user_id else None,
        "session_id": request.cookies.get("session_id") or request.headers.get("x-session-id"),
        "clicked_at": datetime.now(timezone.utc),
    })

    return {"ok": True}
