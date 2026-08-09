"""Read-only hotel-scoped financial reconciliation reports."""

from .routes import api_router
from .overview import build_operations_overview
from .service import build_reconciliation_report
from .domain_events import (
    append_domain_event,
    backfill_domain_events,
    ensure_domain_event_collections,
    get_hotel_financial_aggregate,
    rebuild_hotel_financial_aggregate,
)

__all__ = [
    "api_router",
    "build_operations_overview",
    "build_reconciliation_report",
    "append_domain_event",
    "backfill_domain_events",
    "ensure_domain_event_collections",
    "get_hotel_financial_aggregate",
    "rebuild_hotel_financial_aggregate",
]
