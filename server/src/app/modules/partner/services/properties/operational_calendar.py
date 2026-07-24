from __future__ import annotations

from datetime import date as date_type, timedelta
from typing import Any

from src.database.connection import get_database


def _build_date_range(year: int, month: int) -> tuple[str, str]:
    first = date_type(year, month, 1)
    if month == 12:
        last = date_type(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date_type(year, month + 1, 1) - timedelta(days=1)
    return first.isoformat(), last.isoformat()


def operational_calendar(prop_id: int, year: int, month: int) -> dict[str, Any]:
    start_date, end_date = _build_date_range(year, month)
    db = get_database()

    # ── Static operational flags ──
    from src.app.modules.partner.services.dashboard.operations import _operational_flags
    operational = _operational_flags(prop_id)

    # ── Hotel rooms (individual room numbers per room type) ──
    hotel_rooms = list(db.hotel_rooms.find(
        {"prop_id": prop_id, "is_active": True},
        {"_id": 0, "room_type_id": 1, "room_label": 1},
    ))
    rooms_by_rt: dict[str, list[str]] = {}
    for hr in hotel_rooms:
        rt_id = hr["room_type_id"]
        rooms_by_rt.setdefault(rt_id, []).append(str(hr.get("room_label", "")))

    # ── Room types ──
    room_types = list(db.room_types.find(
        {"prop_id": prop_id},
        {"_id": 0, "room_type_id": 1, "name": 1},
    ))
    all_rt_ids = [rt["room_type_id"] for rt in room_types]

    # ── All room numbers for the property ──
    all_room_numbers: list[str] = []
    for rt_id in all_rt_ids:
        all_room_numbers.extend(rooms_by_rt.get(rt_id, []))

    # ── Rate calendar entries ──
    rate_entries = list(db.hotel_rate_calendar.find(
        {"prop_id": prop_id, "date": {"$gte": start_date, "$lte": end_date}},
        {"_id": 0, "date": 1, "rate_plan_id": 1, "rate_amount": 1, "plan_name": 1},
    ))
    rates_by_date: dict[str, list[dict[str, Any]]] = {}
    for entry in rate_entries:
        rates_by_date.setdefault(entry["date"], []).append(entry)

    # ── Inventory calendar (exclude deleted) ──
    inventory_entries = list(db.room_inventory_calendar.find(
        {
            "prop_id": prop_id,
            "date": {"$gte": start_date, "$lte": end_date},
            "$or": [{"is_deleted": {"$ne": True}}, {"is_deleted": {"$exists": False}}],
        },
        {"_id": 0, "date": 1, "room_type_id": 1, "total_rooms": 1, "available_rooms": 1, "blocked_rooms": 1},
    ))
    inv_by_rt_and_date: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for entry in inventory_entries:
        inv_by_rt_and_date.setdefault(entry["room_type_id"], {}).setdefault(entry["date"], []).append(entry)

    # ── Active promotions ──
    active_promotions = list(db.promotion_campaigns.find(
        {"prop_id": prop_id, "is_active": True},
        {"_id": 0, "start_date": 1, "end_date": 1, "name": 1},
    ))

    # ── Build day headers ──
    day_headers: list[dict[str, Any]] = []
    current = date_type.fromisoformat(start_date)
    end = date_type.fromisoformat(end_date)
    while current <= end:
        day_headers.append({
            "date": current.isoformat(),
            "dayOfWeek": current.weekday(),
            "isToday": current == date_type.today(),
        })
        current += timedelta(days=1)

    # ── Build single row: per-day operational status ──
    days: list[dict[str, Any]] = []
    for dh in day_headers:
        d = dh["date"]
        day_rates = rates_by_date.get(d, [])
        best_rate = None
        best_rate_plan = None
        for r in day_rates:
            amt = r.get("rate_amount")
            if amt is not None and (best_rate is None or amt < best_rate):
                best_rate = amt
                best_rate_plan = r.get("plan_name") or r.get("rate_plan_id")

        has_promo = any(
            prom["start_date"] <= d <= prom["end_date"]
            for prom in active_promotions
        )

        # Aggregate inventory per room type for this day
        total_rooms = 0
        available_rooms = 0
        blocked_rooms = 0
        has_inventory_today = False
        rooms_with_data: list[dict[str, Any]] = []
        for rt in room_types:
            rt_id = rt["room_type_id"]
            day_inv = inv_by_rt_and_date.get(rt_id, {}).get(d, [])
            if day_inv:
                has_inventory_today = True
                inv = day_inv[0]
                t = inv.get("total_rooms", 0) or 0
                a = inv.get("available_rooms", 0) or 0
                b = inv.get("blocked_rooms", 0) or 0
                total_rooms += t
                available_rooms += a
                blocked_rooms += b
                room_nums = rooms_by_rt.get(rt_id, [])
                rooms_with_data.append({
                    "roomTypeId": rt_id,
                    "roomTypeName": rt.get("name", rt_id),
                    "roomNumbers": room_nums,
                    "available": a,
                    "availableStatus": "disponible" if a > 0 else "bloqueada",
                    "blocked": b > 0,
                    "total": t,
                })

        days.append({
            "date": d,
            "hasRate": len(day_rates) > 0,
            "rateCount": len(day_rates),
            "bestRate": best_rate,
            "bestRatePlan": best_rate_plan,
            "hasPromotion": has_promo,
            "hasInventory": has_inventory_today,
            "totalRooms": total_rooms,
            "availableRooms": available_rooms,
            "blockedRooms": blocked_rooms,
            "roomNumbers": all_room_numbers,
            "rooms": rooms_with_data,
        })

    return {
        "year": year,
        "month": month,
        "operational": operational,
        "dayHeaders": day_headers,
        "days": days,
        "roomCount": len(all_room_numbers),
        "roomNumbers": all_room_numbers,
    }
