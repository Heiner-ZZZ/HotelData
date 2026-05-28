from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates

from src.app.modules.admin.service import security_overview, users_overview
from src.app.security.dependencies import require_permission


router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[2] / "templates"))


@router.get("/security")
def security_dashboard(request: Request, current_user: dict = Depends(require_permission("users.manage"))):
    return templates.TemplateResponse(
        request,
        "admin/security.html",
        {
            "current_user": current_user,
            "overview": security_overview(),
        },
    )


@router.get("/users")
def users_dashboard(request: Request, current_user: dict = Depends(require_permission("users.manage"))):
    return templates.TemplateResponse(
        request,
        "admin/users.html",
        {
            "current_user": current_user,
            "overview": users_overview(),
        },
    )
