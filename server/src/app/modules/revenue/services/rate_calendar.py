"""R2.2 — Calendario de tarifas: días con tarifa vs huecos (lectura Mongo).

Informe simple del TA12: consulta ``hotel_rate_calendar`` + ``rate_plans``
directamente en Mongo (sin ETL). Devuelve resumen (planes activos, tarifa
media, días cerrados, huecos), serie diaria para el gráfico central y filas
paginadas para la grilla del patrón Z.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from typing import Any

from src.database.connection import get_database


def _default_range(days: int = 90) -> tuple[date, date]:
    end = datetime.now(timezone.utc).date()
    return end - timedelta(days=days - 1), end


def get_rate_calendar_dashboard(
    *,
    prop_id: int | None = None,
    plan_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    days: int = 90,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Resumen + serie + grilla del calendario de tarifas (Mongo)."""
    start = date.fromisoformat(date_from) if date_from else _default_range(days)[0]
    end = date.fromisoformat(date_to) if date_to else _default_range(days)[1]
    if end < start:
        raise ValueError("date_to debe ser igual o posterior a date_from")
    if page < 1 or page_size < 1:
        raise ValueError("page y page_size deben ser mayores que cero")

    db = get_database()
    match: dict[str, Any] = {"date": {"$gte": start.isoformat(), "$lte": end.isoformat()}}
    if prop_id:
        match["prop_id"] = prop_id
    if plan_id:
        match["rate_plan_id"] = plan_id

    plan_match = {"prop_id": prop_id} if prop_id else {}
    plans = list(
        db.rate_plans.find(
            plan_match,
            {"_id": 0, "rate_plan_id": 1, "name": 1, "base_rate": 1, "currency": 1, "is_active": 1},
        ).sort("name", 1)
    )
    plan_map = {p["rate_plan_id"]: p for p in plans}

    docs = list(
        db.hotel_rate_calendar.find(match, {"_id": 0}).sort([("date", 1), ("rate_plan_id", 1)])
    )

    # ── Resumen ──
    total = len(docs)
    closed = sum(1 for r in docs if r.get("is_closed"))
    open_entries = total - closed
    rates = [float(r.get("rate_amount") or 0) for r in docs if not r.get("is_closed") and r.get("rate_amount")]
    avg_rate = sum(rates) / len(rates) if rates else 0.0
    min_rate = min(rates) if rates else 0.0
    max_rate = max(rates) if rates else 0.0

    distinct_dates = sorted({r["date"] for r in docs})
    date_set = set(distinct_dates)
    expected_dates = [
        (start + timedelta(days=i)).isoformat()
        for i in range((end - start).days + 1)
    ]
    gap_dates = [d for d in expected_dates if d not in date_set]
    active_plans = [p for p in plans if p.get("is_active", True)]

    # ── Desglose por plan: min/max/avg tarifa + entradas abiertas/cerradas ──
    by_plan: dict[str, dict[str, Any]] = {}
    for r in docs:
        pid = r.get("rate_plan_id")
        bucket = by_plan.setdefault(pid, {
            "rate_plan_id": pid,
            "plan_name": plan_map.get(pid, {}).get("name") or pid,
            "entries": 0,
            "closed": 0,
            "rates": [],
            "currency": plan_map.get(pid, {}).get("currency") or "USD",
        })
        bucket["entries"] += 1
        if r.get("is_closed"):
            bucket["closed"] += 1
        elif r.get("rate_amount") is not None:
            bucket["rates"].append(float(r["rate_amount"]))
    by_plan_list: list[dict[str, Any]] = []
    for pid, b in by_plan.items():
        rates_b = b["rates"]
        by_plan_list.append({
            "rate_plan_id": pid,
            "plan_name": b["plan_name"],
            "entries": b["entries"],
            "closed": b["closed"],
            "open": b["entries"] - b["closed"],
            "min_rate": round(min(rates_b), 2) if rates_b else 0.0,
            "max_rate": round(max(rates_b), 2) if rates_b else 0.0,
            "avg_rate": round(sum(rates_b) / len(rates_b), 2) if rates_b else 0.0,
            "currency": b["currency"],
        })
    by_plan_list.sort(key=lambda item: item["plan_name"])

    # ── Serie diaria: tarifa media + días cerrados por fecha ──
    daily: dict[str, dict[str, Any]] = {}
    for r in docs:
        day = r["date"]
        bucket = daily.setdefault(day, {"rate_sum": 0.0, "rate_count": 0, "closed": 0})
        if r.get("is_closed"):
            bucket["closed"] += 1
        elif r.get("rate_amount") is not None:
            bucket["rate_sum"] += float(r["rate_amount"])
            bucket["rate_count"] += 1

    def _avg(day: str) -> float:
        bucket = daily.get(day)
        if not bucket or not bucket["rate_count"]:
            return 0.0
        return round(bucket["rate_sum"] / bucket["rate_count"], 2)

    series = {
        "labels": expected_dates,
        "datasets": [
            {"label": "Tarifa media", "data": [_avg(d) for d in expected_dates]},
            {"label": "Días cerrados", "data": [daily.get(d, {}).get("closed", 0) for d in expected_dates]},
        ],
    }

    # ── Grilla con nombre de plan ──
    enriched: list[dict[str, Any]] = []
    for r in docs:
        plan = plan_map.get(r.get("rate_plan_id"), {})
        enriched.append({
            "date": r.get("date"),
            "prop_id": r.get("prop_id"),
            "rate_plan_id": r.get("rate_plan_id"),
            "plan_name": plan.get("name") or r.get("rate_plan_id"),
            "rate_amount": round(float(r.get("rate_amount") or 0), 2),
            "min_stay_nights": int(r.get("min_stay_nights") or 0),
            "is_closed": bool(r.get("is_closed", False)),
            "currency": plan.get("currency") or "USD",
        })

    total_pages = max(1, math.ceil(total / page_size))
    page_rows = enriched[(page - 1) * page_size : page * page_size]

    return {
        "available": True,
        "source": "mongodb",
        "date_from": start.isoformat(),
        "date_to": end.isoformat(),
        "prop_id": prop_id,
        "summary": {
            "total_entries": total,
            "plans": len(plans),
            "active_plans": len(active_plans),
            "avg_rate": round(avg_rate, 2),
            "min_rate": round(min_rate, 2),
            "max_rate": round(max_rate, 2),
            "closed_days": closed,
            "open_days": open_entries,
            "distinct_dates": len(distinct_dates),
            "gap_days": len(gap_dates),
            "range_days": len(expected_dates),
            "has_data": bool(docs),
        },
        "by_plan": by_plan_list,
        "series": series,
        "rows": page_rows,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page * page_size < total,
        "has_prev": page > 1,
    }
