from __future__ import annotations

from src.app.modules.revenue.schemas import ModuleStatus


def module_status() -> ModuleStatus:
    return ModuleStatus(
        module="revenue",
        status="planned",
        description="Preparado para tarifas, promociones y revenue futuro; GA03 solo analiza datos existentes.",
    )
