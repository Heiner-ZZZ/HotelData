"""KPI data endpoints for page-level charts (rooms, rates, policies, check-ins, check-outs)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Query
from pymongo import ASCENDING, DESCENDING

from src.database.connection import get_database

router = APIRouter(prefix="/api/kpi", tags=["kpi"])


@router.get("/top-hotels/rooms")
def top_hotels_by_rooms(limit: int = Query(default=5, ge=1, le=20)):
    """Top N hotels with the most room types and physical rooms."""
    db = get_database()

    pipeline = [
        {
            "$group": {
                "_id": "$prop_id",
                "room_types": {"$sum": 1},
            }
        },
        {"$sort": {"room_types": -1}},
        {"$limit": limit},
    ]
    rooms_by_prop = list(db.room_types.aggregate(pipeline))
    prop_ids = [item["_id"] for item in rooms_by_prop if item["_id"]]

    # Look up hotel names
    hotel_lookup = {}
    if prop_ids:
        for doc in db.dim_hotels.find(
            {"prop_id": {"$in": prop_ids}},
            {"_id": 0, "prop_id": 1, "hotel_name": 1, "display_name": 1},
        ):
            hotel_lookup[doc["prop_id"]] = doc.get("display_name") or doc.get("hotel_name") or f"Hotel #{doc['prop_id']}"

    items = []
    for item in rooms_by_prop:
        pid = item["_id"]
        # Count physical rooms for this prop
        physical = db.hotel_rooms.count_documents({"prop_id": pid, "is_active": True})
        items.append({
            "prop_id": pid,
            "label": hotel_lookup.get(pid, f"Hotel #{pid}"),
            "room_types": item["room_types"],
            "physical_rooms": physical,
        })

    return {"items": items}


@router.get("/rate-trend")
def rate_trend_7d(limit_plans: int = Query(default=5, ge=1, le=20)):
    """Average daily rate per rate plan over the last 7 days (line chart data)."""
    db = get_database()

    # Calculate last 7 days
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    seven_days_ago = today - timedelta(days=6)
    date_strs = [(seven_days_ago + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    # Get top rate plans by calendar entries
    pipeline = [
        {"$group": {"_id": "$rate_plan_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit_plans},
    ]
    top_plans = list(db.hotel_rate_calendar.aggregate(pipeline))
    plan_ids = [item["_id"] for item in top_plans if item["_id"]]

    # Look up plan names
    plan_names = {}
    if plan_ids:
        for doc in db.rate_plans.find(
            {"rate_plan_id": {"$in": plan_ids}},
            {"_id": 0, "rate_plan_id": 1, "name": 1, "prop_id": 1},
        ):
            plan_names[doc["rate_plan_id"]] = doc.get("name") or doc["rate_plan_id"]

    # For each plan, get avg rate per date
    series = []
    for pid in plan_ids:
        pipeline = [
            {"$match": {"rate_plan_id": pid, "date": {"$in": date_strs}}},
            {
                "$group": {
                    "_id": "$date",
                    "avg_rate": {"$avg": "$rate_amount"},
                }
            },
            {"$sort": {"_id": ASCENDING}},
        ]
        daily_data = list(db.hotel_rate_calendar.aggregate(pipeline))
        date_map = {d["_id"]: round(d["avg_rate"], 2) for d in daily_data}

        series.append({
            "plan_id": pid,
            "plan_name": plan_names.get(pid, pid),
            "data": [{"date": d, "avg_rate": date_map.get(d, 0)} for d in date_strs],
        })

    return {"dates": date_strs, "series": series}


@router.get("/operational-stats")
def operational_stats():
    """Global operational counts for policies, check-ins, check-outs, and hotels."""
    db = get_database()

    # Total hotels
    total_hotels = db.dim_hotels.count_documents({})

    # Policies count
    policies_count = db.hotel_policies.count_documents({})
    hotels_with_policies = len(db.hotel_policies.distinct("prop_id"))

    # Today's check-ins and check-outs
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    check_ins_today = db.booking_orders.count_documents({"check_in_date": today})
    check_outs_today = db.booking_orders.count_documents({"check_out_date": today})

    # Check-ins per hotel (top 5)
    pipeline = [
        {"$match": {"check_in_date": today}},
        {"$group": {"_id": "$prop_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5},
    ]
    check_ins_by_hotel = list(db.booking_orders.aggregate(pipeline))

    # Check-outs per hotel (top 5)
    pipeline2 = [
        {"$match": {"check_out_date": today}},
        {"$group": {"_id": "$prop_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5},
    ]
    check_outs_by_hotel = list(db.booking_orders.aggregate(pipeline2))

    # Enrich with hotel names
    prop_ids = set()
    for item in check_ins_by_hotel + check_outs_by_hotel:
        if item.get("_id"):
            prop_ids.add(item["_id"])

    hotel_lookup = {}
    if prop_ids:
        for doc in db.dim_hotels.find(
            {"prop_id": {"$in": list(prop_ids)}},
            {"_id": 0, "prop_id": 1, "hotel_name": 1, "display_name": 1},
        ):
            hotel_lookup[doc["prop_id"]] = doc.get("display_name") or doc.get("hotel_name") or f"Hotel #{doc['prop_id']}"

    def _enrich(items):
        result = []
        for item in items:
            pid = item.get("_id")
            if pid:
                result.append({
                    "prop_id": pid,
                    "label": hotel_lookup.get(pid, f"Hotel #{pid}"),
                    "count": item["count"],
                })
        return result

    return {
        "total_hotels": total_hotels,
        "total_policies": policies_count,
        "hotels_with_policies": hotels_with_policies,
        "check_ins_today": check_ins_today,
        "check_outs_today": check_outs_today,
        "check_ins_by_hotel": _enrich(check_ins_by_hotel),
        "check_outs_by_hotel": _enrich(check_outs_by_hotel),
    }
