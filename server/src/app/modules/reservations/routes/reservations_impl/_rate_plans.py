"""Rate plans — list available plans with rates and validate eligibility."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from fastapi import HTTPException

from src.app.modules.partner.services.rates.plans import filter_eligible_plans
from src.database.connection import get_database


def list_rate_plans_with_rates(
    prop_id: int,
    check_in: str,
    check_out: str,
    room_type_id: str = "",
) -> dict:
    """Return available rate plans for a hotel + date range + optional room type.

    Each plan includes its calendar rates so the user can compare prices.
    """
    db = get_database()
    try:
        cin = date.fromisoformat(check_in)
        cout = date.fromisoformat(check_out)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid date format")

    dates = [(cin + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(max(1, (cout - cin).days))]

    match: dict[str, Any] = {"prop_id": prop_id, "date": {"$in": dates}}
    if room_type_id:
        match["room_type_id"] = room_type_id

    calendar_entries = list(
        db.hotel_rate_calendar.find(match, {"_id": 0, "rate_plan_id": 1, "rate_amount": 1, "date": 1, "currency": 1})
        .sort([("rate_plan_id", 1), ("date", 1)])
    )

    if not calendar_entries:
        return {"rate_plans": []}

    # Group by rate_plan_id
    plan_groups: dict[str, dict[str, Any]] = {}
    for entry in calendar_entries:
        pid = entry.get("rate_plan_id", "")
        if not pid:
            continue
        if pid not in plan_groups:
            plan_groups[pid] = {
                "rate_plan_id": pid,
                "rates": [],
                "avg_rate": 0.0,
                "currency": entry.get("currency", "USD"),
            }
        plan_groups[pid]["rates"].append({
            "date": entry["date"],
            "rate_amount": entry["rate_amount"],
        })

    # Calculate average rate per plan and enrich with plan metadata
    plan_ids = list(plan_groups.keys())
    plans_meta = list(db.rate_plans.find(
        {"rate_plan_id": {"$in": plan_ids}},
        {"_id": 0, "rate_plan_id": 1, "name": 1, "description": 1, "base_rate": 1, "currency": 1, "is_active": 1},
    ))
    meta_by_id = {p["rate_plan_id"]: p for p in plans_meta}

    result = []
    for pid, group in plan_groups.items():
        meta = meta_by_id.get(pid, {})
        rates = group["rates"]
        avg_rate = round(sum(r["rate_amount"] for r in rates) / len(rates), 2) if rates else 0
        total = round(sum(r["rate_amount"] for r in rates), 2)
        result.append({
            "rate_plan_id": pid,
            "name": meta.get("name", pid),
            "description": meta.get("description", ""),
            "base_rate": meta.get("base_rate"),
            "currency": group["currency"] or meta.get("currency", "USD"),
            "is_active": meta.get("is_active", True),
            "avg_rate_per_night": avg_rate,
            "total_price": total,
            "nights": len(rates),
        })

    # Filter out inactive plans and sort by price
    result = [p for p in result if p["is_active"]]
    result.sort(key=lambda p: p["total_price"])

    return {"rate_plans": result}


def validate_rate_plan_eligibility(
    payload: dict,
    user_role: str,
) -> str | None:
    """Check if the rate plans for the selected dates/room type are eligible for the user role."""
    if not user_role or user_role == "super_admin":
        return None
    prop_id = payload.get("prop_id")
    room_type_id = payload.get("room_type_id", "")
    check_in = payload.get("check_in_date", "")
    check_out = payload.get("check_out_date", "")
    if not all([prop_id, check_in, check_out]):
        return None
    db = get_database()
    try:
        cin = date.fromisoformat(check_in)
        cout = date.fromisoformat(check_out)
    except (ValueError, TypeError):
        return None
    total_nights = max(1, (cout - cin).days)
    dates = [(cin + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(total_nights)]

    match: dict[str, object] = {"prop_id": prop_id, "date": {"$in": dates}}
    if room_type_id:
        match["room_type_id"] = room_type_id
    records = list(
        db.hotel_rate_calendar.find(match, {"_id": 0, "rate_plan_id": 1}).limit(50)
    )
    # Collect unique rate_plan_ids
    plan_ids: set[str] = set()
    for r in records:
        pid = r.get("rate_plan_id", "")
        if pid:
            plan_ids.add(pid)
    if not plan_ids:
        return None
    # Fetch the plans
    plans = list(
        db.rate_plans.find(
            {"rate_plan_id": {"$in": list(plan_ids)}},
            {"_id": 0, "rate_plan_id": 1, "name": 1, "eligible_roles": 1},
        )
    )
    eligible_plans = filter_eligible_plans(plans, user_role=user_role)
    if len(eligible_plans) < len(plans):
        ineligible_names: list[str] = []
        eligible_ids = {p["rate_plan_id"] for p in eligible_plans if "rate_plan_id" in p}
        for plan in plans:
            if plan.get("rate_plan_id") not in eligible_ids:
                ineligible_names.append(plan.get("name") or plan.get("rate_plan_id", "?"))
        return (
            "No tienes acceso a los planes tarifarios de este hotel. "
            f"Plan(es) no elegible(s): {', '.join(ineligible_names)}."
        )
    return None
