from __future__ import annotations

from src.app.modules.global_settings.service import (
    ensure_global_settings_collections,
    get_platform_config,
    update_platform_config,
    list_global_hotels,
    get_hotel_global_data,
    update_hotel_global_data,
    list_tax_rates,
    upsert_tax_rate,
    delete_tax_rate,
    list_commission_rates,
    upsert_commission_rate,
    delete_commission_rate,
)

__all__ = [
    "ensure_global_settings_collections",
    "get_platform_config",
    "update_platform_config",
    "list_global_hotels",
    "get_hotel_global_data",
    "update_hotel_global_data",
    "list_tax_rates",
    "upsert_tax_rate",
    "delete_tax_rate",
    "list_commission_rates",
    "upsert_commission_rate",
    "delete_commission_rate",
]
