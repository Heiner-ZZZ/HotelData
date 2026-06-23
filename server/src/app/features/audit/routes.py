from __future__ import annotations

from fastapi import APIRouter

from src.app.features.audit.service import recent_activity


router = APIRouter()


@router.get("/audit")
def audit():
    return {"activity": recent_activity()}


@router.get("/api/audit/activity")
def api_audit_activity():
    return recent_activity()
