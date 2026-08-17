from __future__ import annotations

from fastapi import Depends, Query

from src.app.modules.partner.routes import api_router
from src.app.modules.partner.services import management_reports_summary
from src.app.security.dependencies import require_permission


@api_router.get("/reports")
def reports_api(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: dict = Depends(require_permission("reports.read")),
):
    return management_reports_summary(user=current_user, page=page, page_size=page_size)
