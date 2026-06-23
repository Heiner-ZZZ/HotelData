from __future__ import annotations

from fastapi import Depends

from src.app.modules.partner.routes import api_router
from src.app.modules.partner.services import management_reports_summary
from src.app.security.dependencies import require_login


@api_router.get("/reports")
def reports_api(current_user: dict = Depends(require_login)):
    return management_reports_summary(user=current_user)
