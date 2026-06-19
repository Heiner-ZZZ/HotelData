from __future__ import annotations

from typing import Any

from src.app.modules.partner.services.dashboard.widgets import (
    _dashboard_arrivals_today,
    _dashboard_quick_stats,
    _dashboard_revenue_chart,
)
from src.app.modules.partner.services.properties import list_partner_hotels
from src.database.connection import get_database


def properties_dashboard(query: str = "", page: int = 1, page_size: int = 20) -> dict[str, Any]:
    db = get_database()
    quick_stats = _dashboard_quick_stats(db)
    revenue_chart = _dashboard_revenue_chart(db)
    arrivals = _dashboard_arrivals_today(db)
    props_list = list_partner_hotels(query, page=page, page_size=page_size)
    return {
        "quick_stats": quick_stats,
        "revenue_chart": revenue_chart,
        "arrivals_today": arrivals,
        "properties": props_list,
    }
