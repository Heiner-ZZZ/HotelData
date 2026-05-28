from __future__ import annotations

from src.app.modules.auth.schemas import ModuleStatus


def module_status() -> ModuleStatus:
    return ModuleStatus(
        module="auth",
        status="planned",
        description="Preparado para autenticacion futura; no implementa login real en GA03.",
    )
