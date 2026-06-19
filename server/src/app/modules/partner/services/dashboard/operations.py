from __future__ import annotations

from typing import Any

from src.database.connection import get_database


def _collection_count(collection_name: str, filters: dict[str, Any] | None = None) -> int:
    db = get_database()
    return int(db[collection_name].count_documents(filters or {}))


def _operational_flags(prop_id: int) -> dict[str, Any]:
    db = get_database()
    policies_count = int(db.hotel_policies.count_documents({"prop_id": prop_id}))
    room_types_count = int(db.room_types.count_documents({"prop_id": prop_id}))
    hotel_rooms_count = int(db.hotel_rooms.count_documents({"prop_id": prop_id}))
    rate_plans_count = int(db.rate_plans.count_documents({"prop_id": prop_id}))
    inventory_count = int(db.room_inventory_calendar.count_documents({"prop_id": prop_id}))
    content_count = int(db.hotel_content_pages.count_documents({"prop_id": prop_id}))
    image_count = int(db.hotel_images.count_documents({"prop_id": prop_id}))
    promotions_count = int(db.promotion_campaigns.count_documents({"prop_id": prop_id, "is_active": True}))
    coupon_count = int(db.coupon_codes.count_documents({"prop_id": prop_id, "is_active": True}))

    policies_ready = policies_count > 0
    rooms_ready = room_types_count > 0
    rates_ready = rate_plans_count > 0
    inventory_ready = inventory_count > 0
    content_ready = content_count > 0 or image_count > 0
    images_ready = image_count > 0
    promotions_ready = promotions_count > 0 or coupon_count > 0

    score = 0
    score += 20 if policies_ready else 0
    score += 20 if rooms_ready else 0
    score += 20 if rates_ready else 0
    score += 20 if inventory_ready else 0
    score += 20 if content_ready else 0

    return {
        "policies_configured": policies_ready,
        "rooms_configured": rooms_ready,
        "rates_configured": rates_ready,
        "inventory_configured": inventory_ready,
        "content_configured": content_ready,
        "images_configured": images_ready,
        "promotions_active": promotions_ready,
        "operational_score": score,
        "counts": {
            "hotel_policies": policies_count,
            "room_types": room_types_count,
            "hotel_rooms": hotel_rooms_count,
            "rate_plans": rate_plans_count,
            "room_inventory_calendar": inventory_count,
            "hotel_content_pages": content_count,
            "hotel_images": image_count,
            "promotion_campaigns": promotions_count,
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
