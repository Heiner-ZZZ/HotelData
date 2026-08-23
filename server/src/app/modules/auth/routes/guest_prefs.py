"""Guest session preferences — lightweight Redis-backed key-value store
for persisting search dates between page navigations.

``PUT /api/guest/session-prefs`` stores a JSON blob keyed by user_id (or
anonymous token). ``GET /api/guest/session-prefs`` retrieves it.

Redis is the persistence layer; when unavailable the endpoint returns 200
with an empty payload instead of 500 — the frontend treats a missing prefs
blob as "no stored dates" (same as first visit).
"""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Request
from pydantic import BaseModel

from src.app.security.dependencies import require_login
from src.cache.cache_service import get_cache, set_cache

api_router = APIRouter(prefix="/api/guest", tags=["guest-prefs"])

SESSION_PREFS_KEY_PREFIX = "guest:session_prefs:"
SESSION_PREFS_TTL_SECONDS = 86_400  # 24 horas


class SessionPrefs(BaseModel):
    check_in: str = ""
    check_out: str = ""
    destination: str = ""
    adults: str = ""
    children: str = ""
    rooms: str = ""


def _prefs_key(user: dict) -> str:
    """Key scoped to the authenticated user_id."""
    return f"{SESSION_PREFS_KEY_PREFIX}{user['_id']}"


@api_router.get("/session-prefs")
def get_session_prefs(
    request: Request,
    current_user: dict = Depends(require_login),
):
    key = _prefs_key(current_user)
    data = get_cache(key)
    if data is None:
        return SessionPrefs().model_dump()
    return data


@api_router.put("/session-prefs")
def put_session_prefs(
    request: Request,
    prefs: SessionPrefs = Body(...),
    current_user: dict = Depends(require_login),
):
    key = _prefs_key(current_user)
    set_cache(key, prefs.model_dump(), ttl_seconds=SESSION_PREFS_TTL_SECONDS)
    return {"ok": True}