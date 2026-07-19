"""Tracking routes — lightweight analytics for user interactions."""

from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Request
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

    try:
        prop_id = int(raw_prop_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="prop_id must be a positive integer") from None

    if prop_id <= 0:
        raise HTTPException(status_code=400, detail="prop_id must be a positive integer")

    if source not in ALLOWED_SOURCES:
        raise HTTPException(status_code=400, detail=f"source must be one of {ALLOWED_SOURCES}")

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
