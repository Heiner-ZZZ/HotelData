"""Pricing and season resolution for booking creation."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from src.database.connection import get_database


def _calculate_total_price(
    prop_id: int,
    room_type_id: str,
    check_in_date: str,
    check_out_date: str,
    rooms: int,
    adults: int = 2,
    children: int = 0,
    discount_percent: int | None = None,
    rate_plan_id: str | None = None,
) -> tuple[float | None, str, int, float, float, bool]:
    """Calculate booking price with occupancy and tax support."""
    db = get_database()
    try:
        check_in = datetime.strptime(check_in_date, "%Y-%m-%d")
        check_out = datetime.strptime(check_out_date, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None, "USD", 0, 0.0, 0.0, False

    total_nights = max(1, (check_out - check_in).days)
    dates = [(check_in + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(total_nights)]
    match: dict[str, Any] = {"prop_id": prop_id, "date": {"$in": dates}}
    if room_type_id:
        match["room_type_id"] = room_type_id
    if rate_plan_id:
        match["rate_plan_id"] = rate_plan_id

    records = list(
        db.hotel_rate_calendar.find(match, {"_id": 0, "date": 1, "rate_amount": 1, "currency": 1, "rate_plan_id": 1}).sort("date", 1)
    )
    if not records:
        return None, "USD", total_nights, 0.0, 0.0, False

    currency = records[0].get("currency", "USD")

    # ── Occupancy-based pricing ──
    rpid = records[0].get("rate_plan_id", "")
    base_occupancy = 2
    extra_adult_price = 0.0
    extra_child_price = 0.0
    tax_included = False
    tax_rate = 0.0
    if rpid:
        plan = db.rate_plans.find_one(
            {"rate_plan_id": rpid},
            {"_id": 0, "base_occupancy": 1, "extra_adult_price": 1, "extra_child_price": 1,
             "tax_included": 1, "tax_rate": 1},
        )
        if plan:
            base_occupancy = int(plan.get("base_occupancy") or 2)
            extra_adult_price = float(plan.get("extra_adult_price") or 0)
            extra_child_price = float(plan.get("extra_child_price") or 0)
            tax_included = bool(plan.get("tax_included", False))
            tax_rate = float(plan.get("tax_rate") or 0)

    # ── Per-date tax overrides ──
    first_record_tax = records[0].get("tax_included")
    first_record_tax_rate = records[0].get("tax_rate")
    if first_record_tax is not None:
        tax_included = bool(first_record_tax)
    if first_record_tax_rate is not None:
        tax_rate = float(first_record_tax_rate)

    total_extra_adults = max(0, adults - base_occupancy * rooms)
    total_extra_children = max(0, children)

    subtotal = 0.0
    for r in records:
        night_rate = float(r.get("rate_amount", 0))
        night_total = night_rate * rooms + total_extra_adults * extra_adult_price + total_extra_children * extra_child_price
        subtotal += night_total

    if discount_percent and discount_percent > 0:
        subtotal = round(subtotal * (1 - discount_percent / 100), 2)

    # ── Tax calculation ──
    tax_amount = 0.0
    if tax_rate > 0 and subtotal > 0:
        if tax_included:
            tax_amount = round(subtotal - subtotal / (1 + tax_rate / 100), 2)
        else:
            tax_amount = round(subtotal * tax_rate / 100, 2)

    total_price = round(subtotal + tax_amount, 2) if not tax_included else round(subtotal, 2)
    if tax_included:
        total_price = round(subtotal, 2)
        tax_amount = round(total_price - total_price / (1 + tax_rate / 100), 2) if tax_rate > 0 else 0.0

    return round(total_price, 2), currency, total_nights, round(tax_rate, 2), round(tax_amount, 2), tax_included


def _resolve_season_id(prop_id: int, check_in_date: str) -> str:
    """Determine the applicable season_id for a given check-in date."""
    if not prop_id or not check_in_date:
        return ""
    db = get_database()
    try:
        check_in = datetime.strptime(check_in_date, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return ""
    rules = list(db.rate_rules.find(
        {"prop_id": prop_id},
        {"_id": 0, "name": 1, "start_date": 1, "end_date": 1},
    ).sort([("start_date", 1)]))
    for rule in rules:
        try:
            r_start = datetime.strptime(str(rule.get("start_date", "")), "%Y-%m-%d").date()
            r_end = datetime.strptime(str(rule.get("end_date", "")), "%Y-%m-%d").date()
            if r_start <= check_in <= r_end:
                slug = str(rule.get("name", "")).strip().lower().replace(" ", "_")
                return slug if slug else ""
        except (ValueError, TypeError):
            continue
    return ""
