"""Rates sub-domain package — split into focused submodules."""

from __future__ import annotations

from .plans import (
    create_rate_plan,
    delete_rate_plan,
    filter_eligible_plans,
    list_rate_plans_for_prop,
    partner_hotel_rates,
    update_rate_plan,
)
from .calendar import (
    batch_update_rate_calendar,
    save_rate_calendar_entry,
)
from .rules import (
    create_seasonal_rule,
    delete_seasonal_rule,
    generate_calendar_from_rules,
    list_seasonal_rules,
    update_seasonal_rule,
)
from .contracts import (
    create_corporate_contract,
    update_corporate_contract,
    delete_corporate_contract,
    list_corporate_contracts,
    validate_contract_code,
    apply_contract_pricing,
)

__all__ = [
    "partner_hotel_rates",
    "create_rate_plan",
    "filter_eligible_plans",
    "update_rate_plan",
    "delete_rate_plan",
    "list_rate_plans_for_prop",
    "save_rate_calendar_entry",
    "batch_update_rate_calendar",
    "create_seasonal_rule",
    "update_seasonal_rule",
    "delete_seasonal_rule",
    "list_seasonal_rules",
    "generate_calendar_from_rules",
    "create_corporate_contract",
    "update_corporate_contract",
    "delete_corporate_contract",
    "list_corporate_contracts",
    "validate_contract_code",
    "apply_contract_pricing",
]
