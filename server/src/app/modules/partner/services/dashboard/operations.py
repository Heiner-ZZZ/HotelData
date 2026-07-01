from __future__ import annotations

from datetime import date
from typing import Any

from src.database.connection import get_database


def _collection_count(collection_name: str, filters: dict[str, Any] | None = None) -> int:
    db = get_database()
    return int(db[collection_name].count_documents(filters or {}))


def _operational_flags(prop_id: int) -> dict[str, Any]:
    db = get_database()
    today_str = date.today().isoformat()

    # ── Checks sin dependencia de fecha ──
    policies_count = int(db.hotel_policies.count_documents({"prop_id": prop_id}))
    hotel_rooms_count = int(db.hotel_rooms.count_documents({"prop_id": prop_id, "is_active": True}))

    # ── Checks DEL DÍA ──
    rates_today = int(db.hotel_rate_calendar.count_documents({"prop_id": prop_id, "date": today_str}))
    inventory_today = int(db.room_inventory_calendar.count_documents({"prop_id": prop_id, "date": today_str}))

    # Promociones activas que cubren hoy
    promotions_count = int(db.promotion_campaigns.count_documents({
        "prop_id": prop_id,
        "is_active": True,
        "start_date": {"$lte": today_str},
        "end_date": {"$gte": today_str},
    }))
    coupon_count = int(db.coupon_codes.count_documents({"prop_id": prop_id, "is_active": True}))

    policies_ready = policies_count > 0
    rooms_ready = hotel_rooms_count > 0
    rates_ready = rates_today > 0
    inventory_ready = inventory_today > 0
    promotions_ready = promotions_count > 0 or coupon_count > 0

    score = 0
    score += 20 if policies_ready else 0
    score += 20 if rooms_ready else 0
    score += 20 if rates_ready else 0
    score += 20 if inventory_ready else 0
    score += 20 if promotions_ready else 0

    return {
        "policies_configured": policies_ready,
        "rooms_configured": rooms_ready,
        "rates_configured": rates_ready,
        "inventory_configured": inventory_ready,
        "promotions_active": promotions_ready,
        "operational_score": score,
        "counts": {
            "hotel_policies": policies_count,
            "hotel_rooms": hotel_rooms_count,
            "hotel_rate_calendar_today": rates_today,
            "room_inventory_calendar_today": inventory_today,
            "promotion_campaigns_active_today": promotions_count,
            "coupon_codes": coupon_count,
        },
    }


def _operational_dashboard_metrics() -> list[dict[str, Any]]:
    metrics = [
        ("Habitaciones configuradas", "room_types"),
        ("Habitaciones físicas", "hotel_rooms"),
        ("Días de inventario", "room_inventory_calendar"),
        ("Planes tarifarios", "rate_plans"),
        ("Tarifas calendario", "hotel_rate_calendar"),
        ("Políticas configuradas", "hotel_policies"),
        ("Contenido hotelero", "hotel_content_pages"),
        ("Imágenes", "hotel_images"),
        ("Campañas", "promotion_campaigns"),
        ("Cupones", "coupon_codes"),
    ]
    return [{"label": label, "value": _collection_count(collection_name)} for label, collection_name in metrics]
