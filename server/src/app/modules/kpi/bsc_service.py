"""Balanced Scorecard (BSC) service — CU-E01 to CU-E08.

Organizes KPIs into 4 perspectives:
- Financiera (Financial)
- Cliente (Customer)
- Procesos Internos (Internal Processes)
- Aprendizaje/Tecnología (Learning & Growth)

Each KPI includes: current value, label, target, unit, semáforo (green/yellow/red),
trend direction, and temporal comparison vs previous period.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from src.database.connection import get_database

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bool_cond(field: str) -> dict[str, Any]:
    return {"$or": [{"$eq": [f"${field}", 1]}, {"$eq": [f"${field}", True]}]}


def _fact_collection(db):
    c = db.fact_hotel_reservations
    if c.estimated_document_count() == 0:
        c = db.fact_hotel_events
    return c


def _semaforo(value: float, target: float) -> str:
    """Return 'green', 'yellow', or 'red' based on threshold."""
    if target <= 0:
        return "green" if value > 0 else "red"
    ratio = value / target
    if ratio >= 0.9:
        return "green"
    if ratio >= 0.7:
        return "yellow"
    return "red"


def _trend(current: float, previous: float) -> str:
    """Return 'up', 'down', or 'stable'."""
    if previous <= 0:
        return "up" if current > 0 else "stable"
    change = (current - previous) / previous
    if change > 0.05:
        return "up"
    if change < -0.05:
        return "down"
    return "stable"


def _pct_change(current: float, previous: float) -> str:
    if previous <= 0:
        return "+∞%" if current > 0 else "0%"
    change = ((current - previous) / previous) * 100
    return f"{'+' if change >= 0 else ''}{change:.1f}%"


def _money(val: float) -> str:
    return f"${val:,.2f}"


def _previous_period_keys() -> tuple[int, int, int, int]:
    """Return (current_start_key, current_end_key, prev_start_key, prev_end_key) as YYYYMMDD integers."""
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    current_end = today - timedelta(days=1)
    current_start = today - timedelta(days=31)
    prev_end = today - timedelta(days=32)
    prev_start = today - timedelta(days=62)
    return (
        int(current_start.strftime("%Y%m%d")),
        int(current_end.strftime("%Y%m%d")),
        int(prev_start.strftime("%Y%m%d")),
        int(prev_end.strftime("%Y%m%d")),
    )


def _fact_aggregate(db, match_filter: dict | None = None, group_id: Any = None) -> dict[str, Any]:
    """Aggregate fact table metrics with optional date filter."""
    fact = _fact_collection(db)
    booked = _bool_cond("reserva_bool")
    clicked = _bool_cond("click_bool")
    promoted = _bool_cond("promotion_flag")

    pipeline: list[dict[str, Any]] = []
    if match_filter:
        pipeline.append({"$match": match_filter})

    group_stage: dict[str, Any] = {
        "$group": {
            "_id": group_id if group_id is not None else None,
            "total_events": {"$sum": 1},
            "total_reservations": {"$sum": {"$cond": [booked, 1, 0]}},
            "total_clicks": {"$sum": {"$cond": [clicked, 1, 0]}},
            "promotions": {"$sum": {"$cond": [promoted, 1, 0]}},
            "avg_price": {"$avg": "$price_usd"},
            "gross_revenue": {"$sum": "$reservas_brutas_usd"},
        }
    }
    pipeline.append(group_stage)

    result = list(fact.aggregate(pipeline, allowDiskUse=True))
    if not result:
        return {"total_events": 0, "total_reservations": 0, "total_clicks": 0, "promotions": 0, "avg_price": 0, "gross_revenue": 0}
    row = result[0]
    row.pop("_id", None)
    for k in ("total_events", "total_reservations", "total_clicks", "promotions"):
        row[k] = int(row.get(k) or 0)
    row["avg_price"] = float(row.get("avg_price") or 0.0)
    row["gross_revenue"] = float(row.get("gross_revenue") or 0.0)
    return row


# ---------------------------------------------------------------------------
# KPI builder
# ---------------------------------------------------------------------------

def _kpi(label: str, value: str, target: float, current_val: float,
         prev_val: float, unit: str = "", detail: str = "",
         higher_is_better: bool = True) -> dict[str, Any]:
    """Build a single KPI with semáforo, trend, and comparison."""
    t = _trend(current_val, prev_val)
    # Invert semáforo if lower is better (e.g. rejected records)
    raw_semaforo = _semaforo(current_val, target) if target > 0 else "green"
    if not higher_is_better:
        # Invert: high value = bad
        if target > 0:
            ratio = current_val / target
            raw_semaforo = "red" if ratio >= 0.9 else ("yellow" if ratio >= 0.7 else "green")
        else:
            raw_semaforo = "green" if current_val == 0 else "red"

    return {
        "label": label,
        "value": value,
        "unit": unit,
        "target": _money(target) if unit == "$" else f"{target:,.0f}",
        "detail": detail,
        "semaforo": raw_semaforo,
        "trend": t,
        "pct_change": _pct_change(current_val, prev_val),
        "current_val": current_val,
        "prev_val": prev_val,
    }


# ---------------------------------------------------------------------------
# Perspectives
# ---------------------------------------------------------------------------

def _financiera() -> list[dict[str, Any]]:
    """Perspective 1: Financial KPIs."""
    db = get_database()
    cs, ce, ps, pe = _previous_period_dates()

    cs_key, ce_key, ps_key, pe_key = _previous_period_keys()
    current = _fact_aggregate(db, match_filter={"date_key": {"$gte": cs_key, "$lte": ce_key}})
    prev = _fact_aggregate(db, match_filter={"date_key": {"$gte": ps_key, "$lte": pe_key}})

    revenue_curr = current["gross_revenue"]
    revenue_prev = prev["gross_revenue"]
    avg_price_curr = current["avg_price"]
    avg_price_prev = prev["avg_price"]
    reservas_curr = current["total_reservations"]
    reservas_prev = prev["total_reservations"]
    rpb_curr = revenue_curr / reservas_curr if reservas_curr else 0
    rpb_prev = revenue_prev / reservas_prev if reservas_prev else 0

    # Target: +15% growth per cycle
    revenue_target = revenue_prev * 1.15 if revenue_prev > 0 else revenue_curr * 1.15

    return [
        _kpi("Revenue Bruto", _money(revenue_curr), revenue_target, revenue_curr, revenue_prev,
             unit="$", detail="Ingreso total por reservas detectadas"),
        _kpi("Precio Promedio", _money(avg_price_curr), avg_price_curr * 1.1 if avg_price_curr > 0 else 200,
             avg_price_curr, avg_price_prev, unit="$", detail="Precio medio por evento"),
        _kpi("Revenue por Reserva", _money(rpb_curr), rpb_curr * 1.1 if rpb_curr > 0 else 0,
             rpb_curr, rpb_prev, unit="$", detail="Ingreso promedio por reserva"),
        _kpi("Reservas Detectadas", f"{reservas_curr:,}", reservas_prev * 1.15 if reservas_prev > 0 else reservas_curr,
             reservas_curr, reservas_prev, detail="Cantidad total de reservas"),
    ]


def _cliente() -> list[dict[str, Any]]:
    """Perspective 2: Customer KPIs."""
    db = get_database()
    cs_key, ce_key, ps_key, pe_key = _previous_period_keys()
    current = _fact_aggregate(db, match_filter={"date_key": {"$gte": cs_key, "$lte": ce_key}})
    prev = _fact_aggregate(db, match_filter={"date_key": {"$gte": ps_key, "$lte": pe_key}})

    events_curr = current["total_events"]
    events_prev = prev["total_events"]
    clicks_curr = current["total_clicks"]
    clicks_prev = prev["total_clicks"]
    reservas_curr = current["total_reservations"]
    reservas_prev = prev["total_reservations"]

    conv_curr = (reservas_curr / events_curr * 100) if events_curr else 0
    conv_prev = (reservas_prev / events_prev * 100) if events_prev else 0
    ctr_curr = (clicks_curr / events_curr * 100) if events_curr else 0
    ctr_prev = (clicks_prev / events_prev * 100) if events_prev else 0

    # Top destinations and countries
    fact = _fact_collection(db)
    top_dest = list(fact.aggregate([
        {"$group": {"_id": "$srch_destination_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}, {"$limit": 5}
    ]))
    top_paises = list(fact.aggregate([
        {"$group": {"_id": "$visitor_location_country_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}, {"$limit": 5}
    ]))

    destinations_detail = ", ".join([str(d["_id"]) for d in top_dest if d.get("_id")]) or "N/A"
    countries_detail = ", ".join([str(c["_id"]) for c in top_paises if c.get("_id")]) or "N/A"

    return [
        _kpi("Tasa de Conversión", f"{conv_curr:.2f}%", 15.0, conv_curr, conv_prev,
             unit="%", detail=f"{reservas_curr:,} reservas / {events_curr:,} eventos"),
        _kpi("Click Rate (CTR)", f"{ctr_curr:.2f}%", 30.0, ctr_curr, ctr_prev,
             unit="%", detail=f"{clicks_curr:,} clicks / {events_curr:,} eventos"),
        _kpi("Top Destinos", f"{len(top_dest)}", 5.0, float(len(top_dest)), float(len(top_dest)),
             detail=f"Destinos principales: {destinations_detail}"),
        _kpi("Mercados Visitantes", f"{len(top_paises)}", 5.0, float(len(top_paises)), float(len(top_paises)),
             detail=f"Países principales: {countries_detail}"),
    ]


def _procesos_internos() -> list[dict[str, Any]]:
    """Perspective 3: Internal Processes KPIs."""
    db = get_database()

    room_types = db.room_types.count_documents({})
    inventory_days = db.room_inventory_calendar.count_documents({})
    rate_plans = db.rate_plans.count_documents({})
    policies = db.hotel_policies.count_documents({})
    content_pages = db.hotel_content_pages.count_documents({})
    images = db.hotel_images.count_documents({})
    campaigns = db.promotion_campaigns.count_documents({})
    bookings = db.booking_orders.count_documents({})

    # Tracking previous values is harder for operational — use static targets
    return [
        _kpi("Tipos de Habitación", f"{room_types:,}", 20.0, float(room_types), float(room_types),
             detail="Total de tipos de habitación configurados"),
        _kpi("Inventario (días)", f"{inventory_days:,}", 1000.0, float(inventory_days), float(inventory_days),
             detail="Días de inventario en calendario"),
        _kpi("Planes Tarifarios", f"{rate_plans:,}", 10.0, float(rate_plans), float(rate_plans),
             detail="Planes de tarifa activos"),
        _kpi("Reservas Operativas", f"{bookings:,}", 100.0, float(bookings), float(bookings),
             detail="Órdenes de reserva registradas"),
        _kpi("Políticas Configuradas", f"{policies:,}", 10.0, float(policies), float(policies),
             detail="Hoteles con políticas definidas"),
        _kpi("Contenido + Imágenes", f"{content_pages + images:,}", 50.0,
             float(content_pages + images), float(content_pages + images),
             detail=f"{content_pages} páginas · {images} imágenes"),
        _kpi("Campañas y Cupones", f"{campaigns:,}", 5.0, float(campaigns), float(campaigns),
             detail="Campañas promocionales activas"),
    ]


def _aprendizaje() -> list[dict[str, Any]]:
    """Perspective 4: Learning & Growth KPIs."""
    db = get_database()

    fact = _fact_collection(db)
    total_records = fact.estimated_document_count()
    rejected = db.rejected_records.count_documents({})
    sessions = db.user_sessions.count_documents({})
    users = db.users.count_documents({})
    activity_logs = db.user_activity_logs.count_documents({})

    # Quality: latest quality report
    latest_quality = db.data_quality_reports.find_one({}, sort=[("generated_at", -1)])
    completeness = float(latest_quality.get("completeness_score", 0)) if latest_quality else 0
    quality_pct = round(completeness * 100, 2)

    return [
        _kpi("Registros Procesados", f"{total_records:,}", 600000.0, float(total_records), float(total_records),
             detail="Registros en fact table (meta: 600K)"),
        _kpi("Calidad de Datos", f"{quality_pct}%", 95.0, quality_pct, quality_pct,
             unit="%", detail="Completitud del dataset (meta: 95%)"),
        _kpi("Registros Rechazados", f"{rejected:,}", 100.0, float(rejected), float(rejected),
             detail="Incidencias de calidad",
             higher_is_better=False),
        _kpi("Usuarios Activos", f"{users:,}", 10.0, float(users), float(users),
             detail=f"{sessions} sesiones activas"),
        _kpi("Traza de Auditoría", f"{activity_logs:,}", 1000.0, float(activity_logs), float(activity_logs),
             detail="Eventos de actividad registrados"),
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_bsc() -> dict[str, Any]:
    """Build the complete Balanced Scorecard payload."""
    now = datetime.now(timezone.utc)
    period_label = f"Últimos 30 días (al {now.strftime('%d/%b/%Y')})"

    perspectives = [
        {
            "id": "financiera",
            "label": "Financiera",
            "icon": "attach_money",
            "description": "Resultados financieros y revenue generado por la plataforma",
            "kpis": _financiera(),
        },
        {
            "id": "cliente",
            "label": "Cliente y Mercado",
            "icon": "groups",
            "description": "Captación digital, conversión y penetración de mercados",
            "kpis": _cliente(),
        },
        {
            "id": "procesos",
            "label": "Procesos Internos",
            "icon": "settings",
            "description": "Eficiencia operativa, configuración hotelera y gestión de reservas",
            "kpis": _procesos_internos(),
        },
        {
            "id": "aprendizaje",
            "label": "Aprendizaje y Tecnología",
            "icon": "auto_awesome",
            "description": "Infraestructura, calidad de datos, seguridad y trazabilidad",
            "kpis": _aprendizaje(),
        },
    ]

    return {
        "generated_at": now.isoformat(),
        "period_label": period_label,
        "perspectives": perspectives,
        "summary": _build_summary(perspectives),
    }


def _build_summary(perspectives: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute overall BSC health score from already-built perspectives."""
    all_kpis = [kpi for p in perspectives for kpi in p["kpis"]]
    total = len(all_kpis)
    if total == 0:
        return {"score": 0, "green": 0, "yellow": 0, "red": 0, "label": "Sin datos"}

    green = sum(1 for k in all_kpis if k["semaforo"] == "green")
    yellow = sum(1 for k in all_kpis if k["semaforo"] == "yellow")
    red = sum(1 for k in all_kpis if k["semaforo"] == "red")
    score = round((green / total) * 100, 1)

    label = "Excelente" if score >= 80 else ("Bueno" if score >= 60 else ("Regular" if score >= 40 else "Crítico"))
    return {
        "score": score,
        "green": green,
        "yellow": yellow,
        "red": red,
        "total": total,
        "label": label,
    }
