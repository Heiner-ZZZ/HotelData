"""Hotel products: billable items/perks that can be added to bookings.

Each hotel can define products (e.g. "Cama extra", "Desayuno", "Parking")
with a unit price and available quantity. These products can be added
to active reservations as line items during the guest's stay.
"""

from __future__ import annotations

import logging
from typing import Any

from src.app.modules.partner.services._common import clean_text, now_utc
from src.database.connection import get_database

logger = logging.getLogger(__name__)


def list_hotel_products(prop_id: int) -> list[dict[str, Any]]:
    """List all billable products for a hotel."""
    db = get_database()
    items = list(
        db.hotel_products.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("category", 1), ("name", 1)])
    )
    for item in items:
        item.setdefault("unit_price", 0.0)
        item.setdefault("quantity_available", 0)
        item.setdefault("is_active", True)
    return items


def create_hotel_product(
    prop_id: int,
    *,
    name: str,
    description: str = "",
    unit_price: float = 0.0,
    quantity_available: int = 0,
    category: str = "Otros",
    is_active: bool = True,
    changed_by: str = "system",
) -> dict[str, Any]:
    """Create a new billable product for a hotel."""
    db = get_database()
    import secrets
    product_id = f"PROD-{secrets.token_hex(4).upper()}"
    doc = {
        "prop_id": prop_id,
        "product_id": product_id,
        "name": clean_text(name),
        "description": clean_text(description),
        "unit_price": round(float(unit_price), 2),
        "quantity_available": int(quantity_available),
        "category": clean_text(category) or "Otros",
        "is_active": bool(is_active),
        "created_by": changed_by,
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    db.hotel_products.insert_one(doc)
    return doc


def update_hotel_product(
    prop_id: int,
    product_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    unit_price: float | None = None,
    quantity_available: int | None = None,
    category: str | None = None,
    is_active: bool | None = None,
    changed_by: str = "system",
) -> dict[str, Any] | None:
    """Update a hotel product."""
    db = get_database()
    set_doc: dict[str, Any] = {"updated_at": now_utc(), "updated_by": changed_by}
    if name is not None:
        set_doc["name"] = clean_text(name)
    if description is not None:
        set_doc["description"] = clean_text(description)
    if unit_price is not None:
        set_doc["unit_price"] = round(float(unit_price), 2)
    if quantity_available is not None:
        set_doc["quantity_available"] = int(quantity_available)
    if category is not None:
        set_doc["category"] = clean_text(category)
    if is_active is not None:
        set_doc["is_active"] = bool(is_active)

    result = db.hotel_products.find_one_and_update(
        {"prop_id": prop_id, "product_id": product_id},
        {"$set": set_doc},
        return_document=True,
        projection={"_id": 0},
    )
    return result


def delete_hotel_product(prop_id: int, product_id: str) -> bool:
    """Delete a hotel product."""
    db = get_database()
    result = db.hotel_products.delete_one({"prop_id": prop_id, "product_id": product_id})
    return result.deleted_count > 0


# ─── Add-on products on active bookings ────────────────────────────────


def list_booking_line_items(booking_id: str) -> list[dict[str, Any]]:
    """Return the line items (add-on products) for a booking."""
    db = get_database()
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "line_items": 1},
    )
    if not booking:
        return []
    return booking.get("line_items", [])


def add_booking_line_item(
    booking_id: str,
    *,
    product_id: str,
    name: str,
    unit_price: float,
    quantity: int = 1,
    changed_by: str = "system",
) -> dict[str, Any] | None:
    """Add a product as a line item to an active booking."""
    db = get_database()
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id, "stay_status": {"$in": ["checked_in", "confirmed"]}},
        {"_id": 0, "stay_status": 1, "prop_id": 1},
    )
    if not booking:
        return None

    total = round(float(unit_price) * int(quantity), 2)
    import secrets
    item_id = f"LI-{secrets.token_hex(4).upper()}"
    line_item = {
        "item_id": item_id,
        "product_id": product_id,
        "name": name,
        "quantity": int(quantity),
        "unit_price": round(float(unit_price), 2),
        "total": total,
        "added_at": now_utc(),
        "added_by": changed_by,
    }

    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {
            "$push": {"line_items": line_item},
            "$set": {"updated_at": now_utc()},
        },
    )

    # Also log in status history
    db.booking_status_history.insert_one({
        "booking_id": booking_id,
        "status": booking.get("stay_status", "confirmed"),
        "changed_at": now_utc(),
        "reason": f"add_on: {name} x{quantity} = ${total}",
        "changed_by": changed_by,
        "is_test": False,
    })

    return line_item


def remove_booking_line_item(
    booking_id: str,
    item_id: str,
    *,
    changed_by: str = "system",
) -> bool:
    """Remove a line item from a booking."""
    db = get_database()
    result = db.booking_orders.update_one(
        {"booking_id": booking_id},
        {
            "$pull": {"line_items": {"item_id": item_id}},
            "$set": {"updated_at": now_utc()},
        },
    )
    if result.modified_count > 0:
        db.booking_status_history.insert_one({
            "booking_id": booking_id,
            "status": "modified",
            "changed_at": now_utc(),
            "reason": f"removed_add_on: {item_id}",
            "changed_by": changed_by,
            "is_test": False,
        })
    return result.modified_count > 0


# ─── Platform Earnings ─────────────────────────────────────────────────


def record_platform_earnings(
    booking_id: str,
    prop_id: int,
    *,
    commission_pct: float,
    booking_total: float,
    commission_amount: float,
) -> dict[str, Any]:
    """Record platform earnings for a booking (called during invoice creation)."""
    db = get_database()
    existing = db.platform_earnings.find_one({"booking_id": booking_id})
    if existing:
        return existing

    doc = {
        "booking_id": booking_id,
        "prop_id": prop_id,
        "commission_pct": commission_pct,
        "booking_total": round(booking_total, 2),
        "commission_amount": round(commission_amount, 2),
        "status": "pending",
        "created_at": now_utc(),
    }
    db.platform_earnings.insert_one(doc)
    return doc


def get_platform_earnings_summary() -> dict[str, Any]:
    """Aggregate platform earnings for the dashboard."""
    db = get_database()
    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_commission": {"$sum": "$commission_amount"},
                "total_bookings": {"$sum": 1},
                "avg_commission": {"$avg": "$commission_amount"},
                "pending_count": {"$sum": {"$cond": [{"$eq": ["$status", "pending"]}, 1, 0]}},
                "paid_count": {"$sum": {"$cond": [{"$eq": ["$status", "paid"]}, 1, 0]}},
            }
        }
    ]
    result = list(db.platform_earnings.aggregate(pipeline))
    if not result:
        return {
            "total_commission": 0.0,
            "total_bookings": 0,
            "avg_commission": 0.0,
            "pending_count": 0,
            "paid_count": 0,
        }
    r = result[0]
    return {
        "total_commission": round(r.get("total_commission", 0), 2),
        "total_bookings": r.get("total_bookings", 0),
        "avg_commission": round(r.get("avg_commission", 0), 2),
        "pending_count": r.get("pending_count", 0),
        "paid_count": r.get("paid_count", 0),
    }


def list_platform_earnings(page: int = 1, page_size: int = 20) -> dict[str, Any]:
    """List all platform earnings records with pagination."""
    db = get_database()
    total = db.platform_earnings.count_documents({})
    cursor = (
        db.platform_earnings.find({}, {"_id": 0})
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = []
    for doc in cursor:
        if isinstance(doc.get("created_at"), datetime):
            doc["created_at"] = doc["created_at"].isoformat()
        # Enrich with hotel name
        hotel = db.dim_hotels.find_one(
            {"prop_id": doc.get("prop_id")},
            {"display_name": 1, "hotel_name": 1, "_id": 0},
        )
        doc["hotel_name"] = (hotel.get("display_name") or hotel.get("hotel_name") or f"Hotel {doc.get('prop_id')}") if hotel else f"Hotel {doc.get('prop_id')}"
        items.append(doc)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size) if total else 1,
    }
