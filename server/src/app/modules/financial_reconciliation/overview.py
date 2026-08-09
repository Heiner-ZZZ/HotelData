"""Read-only hotel operations overview aggregating the connected domains."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.database.connection import get_database


def _sum(db, collection: str, query: dict[str, Any], field: str) -> float:
    rows = list(db[collection].aggregate([
        {"$match": query},
        {"$group": {"_id": None, "value": {"$sum": f"${field}"}}},
    ]))
    return round(float(rows[0].get("value", 0) or 0), 2) if rows else 0.0


def build_operations_overview(prop_id: int) -> dict[str, Any]:
    db = get_database()
    hotel = db.dim_hotels.find_one({"prop_id": prop_id}, {"display_name": 1, "hotel_name": 1})
    if not hotel:
        raise LookupError(f"Hotel {prop_id} no encontrado")

    room_rows = list(db.room_status_log.find({"prop_id": prop_id}, {"status": 1, "hotel_room_id": 1, "room_id": 1, "updated_at": 1, "created_at": 1}))
    # room_status_log is an event/history collection. For occupancy KPIs use
    # only the latest event per physical room; otherwise every historical
    # checkout/check-in inflates the room count.
    latest_by_room: dict[str, dict[str, Any]] = {}
    for row in room_rows:
        room_key = str(row.get("hotel_room_id") or row.get("room_id") or row.get("room_label") or row.get("_id"))
        previous = latest_by_room.get(room_key)
        row_time = row.get("updated_at") or row.get("created_at") or datetime.min.replace(tzinfo=timezone.utc)
        previous_time = (previous or {}).get("updated_at") or (previous or {}).get("created_at") or datetime.min.replace(tzinfo=timezone.utc)
        if previous is None or row_time >= previous_time:
            latest_by_room[room_key] = row
    current_rooms = list(latest_by_room.values())
    occupied = sum(1 for row in current_rooms if row.get("status") in {"occupied_clean", "occupied_dirty"})
    dirty = sum(1 for row in current_rooms if row.get("status") in {"vacant_dirty", "occupied_dirty"})
    maintenance = sum(1 for row in current_rooms if row.get("status") in {"maintenance_requested", "out_of_service", "out_of_order"})
    available = sum(1 for row in current_rooms if row.get("status") == "vacant_clean")

    invoice_query = {"prop_id": prop_id, "status": {"$nin": ["cancelled"]}}
    paid_invoice_query = {"prop_id": prop_id, "status": "paid"}
    payment_query = {"prop_id": prop_id, "status": "confirmed"}
    expense_query = {"prop_id": prop_id, "status": {"$in": ["approved", "paid"]}}
    maintenance_query = {"prop_id": prop_id, "status": {"$ne": "deleted"}}
    open_shift = db.reception_shifts.find_one({"prop_id": prop_id, "status": "open"}, {"_id": 1, "cash_initial": 1})

    return {
        "prop_id": prop_id,
        "hotel": {
            "name": hotel.get("display_name") or hotel.get("hotel_name") or f"Hotel {prop_id}",
        },
        "occupancy": {
            "occupied_rooms": occupied,
            "dirty_rooms": dirty,
            "maintenance_rooms": maintenance,
            "available_rooms": available,
            "total_tracked_rooms": len(current_rooms),
            "reconciliation_status": "ok" if not maintenance else "warning",
        },
        "revenue": {
            "room_revenue": _sum(db, "reservation_invoices", paid_invoice_query, "total"),
            "invoices_issued": _sum(db, "reservation_invoices", invoice_query, "total"),
            "payments_confirmed": _sum(db, "reservation_payments", payment_query, "amount"),
            "outstanding_folio_balance": _sum(db, "guest_folios", {"prop_id": prop_id, "total_due": {"$gt": 0}}, "total_due"),
            "refunds": _sum(db, "reservation_payments", {"prop_id": prop_id, "status": "refunded"}, "amount"),
        },
        "expenses": {
            "approved": _sum(db, "expense_invoices", expense_query, "total"),
            "paid": _sum(db, "expense_invoices", {"prop_id": prop_id, "status": "paid"}, "total"),
            "maintenance_cost": _sum(db, "maintenance_tasks", maintenance_query, "actual_cost"),
            "inventory_purchases": _sum(db, "expense_invoices", {"prop_id": prop_id, "product_lines": {"$exists": True}}, "total"),
        },
        "cash": {
            "open_shift_id": str(open_shift["_id"]) if open_shift else None,
            "expected_cash": round(
                (float(open_shift.get("cash_initial", 0) or 0) if open_shift else 0.0)
                + _sum(db, "reservation_payments", {
                    "prop_id": prop_id,
                    "method": {"$in": ["cash", "efectivo"]},
                    "status": "confirmed",
                    "shift_id": open_shift["_id"] if open_shift else {"$exists": False},
                }, "amount"),
                2,
            ),
            "unresolved_over_short": _sum(db, "reception_shifts", {
                "prop_id": prop_id,
                "status": "closed",
                "cash_over_short": {"$exists": True, "$ne": 0},
            }, "cash_over_short"),
        },
        "alerts": [],
    }
