from __future__ import annotations

from fastapi import APIRouter, Request
from src.app.template_utils import templates

from src.app.features.audit.service import recent_activity


router = APIRouter()


@router.get("/audit")
def audit(request: Request):
    return templates.TemplateResponse(
        request,
        "audit/index.html",
        {"activity": recent_activity()},
    )


@router.get("/api/audit/activity")
def api_audit_activity():
    return recent_activity()
