from __future__ import annotations

from src.app.modules.reservations.schemas import ModuleStatus


def module_status() -> ModuleStatus:
    return ModuleStatus(
        module="reservations",
        status="planned",
        description="Preparado para reservas transaccionales futuras; GA03 mantiene fact_hotel_reservations analitico.",
    )
