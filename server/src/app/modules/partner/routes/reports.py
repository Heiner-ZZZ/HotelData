from __future__ import annotations

from src.app.modules.partner.routes import api_router
from src.app.modules.partner.services import management_reports_summary


@api_router.get("/reports")
def reports_api():
    return management_reports_summary()
