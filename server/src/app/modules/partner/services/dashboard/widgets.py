from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

from src.app.modules.partner.services._common import active_fact_collection, now_utc


def _dashboard_quick_stats(db) -> dict[str, Any]:
    collection, _ = active_fact_collection()
    now = now_utc()
    booked = {"$or": [{"$eq": ["$reserva_bool", 1]}, {"$eq": ["$reserva_bool", True]}]}
    clicked = {"$or": [{"$eq": ["$click_bool", 1]}, {"$eq": ["$click_bool", True]}]}
    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_searches": {"$sum": 1},
                "total_reservations": {"$sum": {"$cond": [booked, 1, 0]}},
                "total_revenue": {"$sum": "$reservas_brutas_usd"},
            }
        },
    ]
    stats = next(collection.aggregate(pipeline, allowDiskUse=True), None)
    total_searches = int(stats["total_searches"]) if stats else 0
    total_reservations = int(stats["total_reservations"]) if stats else 0
    occupancy_rate = round((total_reservations / total_searches) * 100, 1) if total_searches else 0.0
    year, month = now.year, now.month
    date_key_start = int(f"{year}{month:02d}01")
    next_m = month + 1
    next_y = year
    if next_m > 12:
        next_m = 1
        next_y += 1
    date_key_end = int(f"{next_y}{next_m:02d}01")
    mtd = next(collection.aggregate([
        {"$match": {"date_key": {"$gte": date_key_start, "$lt": date_key_end}}},
        {"$group": {"_id": None, "revenue": {"$sum": "$reservas_brutas_usd"}}},
    ], allowDiskUse=True), None)
    revenue_mtd = float(mtd["revenue"]) if mtd else 0.0
    prev_m = month - 1
    prev_y = year
    if prev_m < 1:
        prev_m = 12
        prev_y -= 1
    prev_start = int(f"{prev_y}{prev_m:02d}01")
    prev = next(collection.aggregate([
        {"$match": {"date_key": {"$gte": prev_start, "$lt": date_key_start}}},
        {"$group": {"_id": None, "revenue": {"$sum": "$reservas_brutas_usd"}}},
    ], allowDiskUse=True), None)
    revenue_prev = float(prev["revenue"]) if prev else 0.0
    revenue_trend = round(((revenue_mtd - revenue_prev) / revenue_prev * 100), 1) if revenue_prev else 0.0

    occ_current = next(collection.aggregate([
        {"$match": {"date_key": {"$gte": date_key_start, "$lt": date_key_end}}},
        {"$group": {"_id": None, "reservations": {"$sum": {"$cond": [booked, 1, 0]}}, "searches": {"$sum": 1}}},
    ], allowDiskUse=True), None)
    occ_prev = next(collection.aggregate([
        {"$match": {"date_key": {"$gte": prev_start, "$lt": date_key_start}}},
        {"$group": {"_id": None, "reservations": {"$sum": {"$cond": [booked, 1, 0]}}, "searches": {"$sum": 1}}},
    ], allowDiskUse=True), None)
    cur_rate = round((occ_current["reservations"] / occ_current["searches"]) * 100, 1) if occ_current and occ_current["searches"] else None
    prev_rate = round((occ_prev["reservations"] / occ_prev["searches"]) * 100, 1) if occ_prev and occ_prev["searches"] else None
    if cur_rate is not None and prev_rate is not None and prev_rate != 0:
        occupancy_trend = round(((cur_rate - prev_rate) / prev_rate) * 100, 1)
    elif cur_rate is not None and prev_rate is None:
        occupancy_trend = None
    else:
        occupancy_trend = 0.0

    pending = 0
    try:
        pending = db.booking_orders.count_documents({
            "check_in_date": now.strftime("%Y-%m-%d"),
            "status": {"$in": ["confirmed", "pending"]},
        })
    except Exception:
        logger.exception("Error counting pending check-ins")
    health = None
    try:
        last = db.data_quality_reports.find_one(sort=[("executed_at", -1)], projection={"overall_score": 1, "_id": 0})
        if last and "overall_score" in last:
            health = int(last["overall_score"])
    except Exception:
        logger.exception("Error reading data health score")
    return {
        "occupancy_rate": occupancy_rate,
        "occupancy_trend": occupancy_trend,
        "total_revenue_mtd": round(revenue_mtd, 2),
        "revenue_trend": revenue_trend,
        "pending_checkins": pending,
        "data_health_score": health,
    }


def _dashboard_revenue_chart(db) -> list[dict[str, Any]]:
    collection, _ = active_fact_collection()
    results = list(collection.aggregate([
        {"$match": {"reserva_bool": True}},
        {"$group": {"_id": {"$floor": {"$divide": ["$date_key", 100]}}, "revenue": {"$sum": "$reservas_brutas_usd"}}},
        {"$sort": {"_id": 1}},
        {"$limit": 8},
    ], allowDiskUse=True))
    return [{"period": str(r["_id"]), "revenue": round(float(r["revenue"]), 2)} for r in results]


def _dashboard_arrivals_today(db) -> list[dict[str, Any]]:
    try:
        today = now_utc().strftime("%Y-%m-%d")
        rows = list(db.booking_orders.find({"check_in_date": today, "status": {"$in": ["confirmed", "pending"]}}, {"_id": 0}).limit(20))
        out = []
        for r in rows:
            name = r.get("guest_name", "Invitado")
            parts = name.strip().split()
            initials = "".join(p[0].upper() for p in parts[:2] if p) or "??"
            out.append({
                "guest_name": name,
                "initials": initials,
                "room_type": r.get("room_type", "Standard"),
                "nights": int(r.get("nights", 1) or 1),
                "arrival_time": r.get("arrival_time", "15:00"),
                "status_tag": r.get("booking_source", "standard"),
            })
        return out
    except Exception:
        logger.exception("Error fetching arrivals today")
        return []
