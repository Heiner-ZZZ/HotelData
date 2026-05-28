from __future__ import annotations

from src.app.modules.partner.schemas import ModuleStatus


def module_status() -> ModuleStatus:
    return ModuleStatus(
        module="partner",
        status="planned",
        description="Preparado para Partner Central futuro; no administra propiedades reales en GA03.",
    )
