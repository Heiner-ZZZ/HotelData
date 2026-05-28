from __future__ import annotations

from src.app.modules.hotels.schemas import ModuleStatus


def module_status() -> ModuleStatus:
    return ModuleStatus(
        module="hotels",
        status="planned",
        description="Preparado para catalogo hotelero y detalle tipo marketplace; datos analiticos actuales se mantienen.",
    )
