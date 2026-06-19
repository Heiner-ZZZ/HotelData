from __future__ import annotations

from src.app.modules.hotels.service._helpers import module_status
from src.app.modules.hotels.service.search import (
    get_hotel_search_cards,
    search_hotels,
)
from src.app.modules.hotels.service.detail import (
    get_hotel_detail_view,
    hotel_detail,
    top_destinations_for_hotel,
)
from src.app.modules.hotels.service.compare import (
    compare_hotel_options,
    compare_hotels,
)

__all__ = [
    "compare_hotel_options",
    "compare_hotels",
    "get_hotel_detail_view",
    "get_hotel_search_cards",
    "hotel_detail",
    "module_status",
    "search_hotels",
    "top_destinations_for_hotel",
]
