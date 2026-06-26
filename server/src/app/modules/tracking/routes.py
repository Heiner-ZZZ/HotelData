"""Tracking routes — lightweight analytics for user interactions."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends
from datetime import datetime, timezone

from src.app.security.dependencies import require_login
from src.database.connection import get_database

tracking_api_router = APIRouter(prefix="/api/tracking", tags=["tracking-api"])


@tracking_api_router.post("/hotel-click")
def track_hotel_click(
    payload: dict = Body(...),
    current_user: dict = Depends(require_login),
):
    """Track a click on a hotel detail page from search results or other sources."""
    db = get_database()
    prop_id = payload.get("prop_id")
    source = payload.get("source", "search")

    if not prop_id:
        return {"ok": False, "error": "prop_id is required"}

    db.click_events.insert_one({
        "prop_id": int(prop_id),
        "source": source,
        "user_id": current_user.get("user_id") or current_user.get("sub", ""),
        "clicked_at": datetime.now(timezone.utc),
    })

    return {"ok": True}
