"""Rates routes implementation package."""

from __future__ import annotations

from ._listing import get_hotel_rates_detail, get_rates_options
from ._plans import create_plan, update_plan, delete_plan
from ._seasonal import get_seasonal_rules, create_seasonal, update_seasonal, delete_seasonal
from ._calendar import update_calendar_entry, batch_update_calendar, generate_calendar
from ._contracts import get_contracts, create_contract, update_contract, delete_contract, validate_contract
from ._promotions import create_promotion

__all__ = [
    "get_hotel_rates_detail",
    "get_rates_options",
    "create_plan",
    "update_plan",
    "delete_plan",
    "get_seasonal_rules",
    "create_seasonal",
    "update_seasonal",
    "delete_seasonal",
    "update_calendar_entry",
    "batch_update_calendar",
    "generate_calendar",
    "get_contracts",
    "create_contract",
    "update_contract",
    "delete_contract",
    "validate_contract",
    "create_promotion",
]
