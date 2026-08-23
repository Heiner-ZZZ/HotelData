from __future__ import annotations

from fastapi import Depends, Query

from src.app.modules.partner.routes import api_router
from src.app.modules.partner.services import management_reports_summary
from src.app.security.dependencies import require_any_permission


@api_router.get("/reports")
def reports_api(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    current_user: dict = Depends(require_any_permission("reports.read", "dashboard.read")),
):
    # Opción 2 (2026-08): la página de Reportes (módulo aún global, migración
    # diferida) exige reports.read O dashboard.read — todos los roles staff
    # portan dashboard.read en el template canónico; un cliente (sin ninguno)
    # sigue fuera. Evita que el sync de Fase 5 deje al gerente sin la página.
    return management_reports_summary(user=current_user, page=page, page_size=page_size)
