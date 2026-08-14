"""Informes compuestos TA12 sobre las tablas ``kpi_*`` de ClickHouse.

Cada dashboard lee UNA tabla KPI táctica (agregado diario generado por el ETL
M2C) y devuelve ``summary`` + ``series`` + filas paginadas, con el mismo
contrato de revenue/billing: ``date_from``/``date_to`` (ambos límites), ``days``
como fallback, ``prop_id`` opcional y ``available: false`` con ``message``
cuando ClickHouse no está disponible (nunca un 500). Nunca lee Mongo como
sustituto ni replica documentos.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable

from config.settings import get_settings

# Contrato de columnas por tabla (KEEP IN SYNC con load.TABLES_DDL).
_BOOKING_COLUMNS = (
    "date, prop_id, hotel_label, room_type_id, room_type_label, booking_source, "
    "status, bookings, nights, revenue_usd, adults, children, cancelled"
)
_NIGHTS_COLUMNS = (
    "date, prop_id, hotel_label, room_type_id, room_type_label, currency, "
    "rooms_sold, room_nights, revenue, cancelled_rooms, adults, children"
)
_RATE_COLUMNS = (
    "date, prop_id, hotel_label, rate_plan_id, rate_plan_label, room_type_id, "
    "room_type_label, currency, published_rate, closed"
)
_INVENTORY_COLUMNS = (
    "date, prop_id, hotel_label, room_type_id, room_type_label, "
    "available_rooms, blocked_rooms, total_rooms"
)
_FUNNEL_COLUMNS = (
    "date, visitor_location_country_id, visitor_country_label, "
    "srch_destination_id, destination_label, searches, clicks, reservations, "
    "revenue_usd, avg_booking_window"
)
_FUNNEL_PC_COLUMNS = (
    "date, prop_id, hotel_label, site_id, site_label, "
    "visitor_location_country_id, visitor_country_label, srch_destination_id, "
    "destination_label, searches, clicks, reservations, revenue_usd, "
    "avg_booking_window, avg_length_of_stay, adults, children, rooms"
)

_BOOKING_STATUS_LABELS: dict[str, str] = {
    "confirmed": "Confirmada",
    "cancelled": "Cancelada",
    "canceled": "Cancelada",
    "cancelled_by_guest": "Cancelada por huésped",
    "cancelled_by_hotel": "Cancelada por hotel",
    "pending": "Pendiente",
    "checked_in": "Check-in",
    "checked_out": "Check-out",
    "no_show": "No-show",
    "": "Sin estado",
}


def _default_range(days: int) -> tuple[date, date]:
    end = datetime.now(timezone.utc).date()
    return end - timedelta(days=days - 1), end


def _validate_range(
    date_from: str | None,
    date_to: str | None,
    days: int,
) -> tuple[date, date]:
    """Resuelve el rango: date_from/date_to explícitos o últimos ``days`` días."""
    fallback_from, fallback_to = _default_range(days)
    start = date.fromisoformat(date_from) if date_from else fallback_from
    end = date.fromisoformat(date_to) if date_to else fallback_to
    if end < start:
        raise ValueError("date_to debe ser igual o posterior a date_from")
    return start, end


def _row_to_dict(names: list[str], row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        name: (value.isoformat() if hasattr(value, "isoformat") else value)
        for name, value in zip(names, row)
    }


def _round2(value: float) -> float:
    return round(float(value or 0), 2)


def _dashboard(
    *,
    table: str,
    columns: str,
    order_by: str,
    summary_fn: Callable[[list[dict[str, Any]]], dict[str, Any]],
    series_fn: Callable[[list[dict[str, Any]]], dict[str, Any]],
    prop_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    days: int = 30,
    page: int = 1,
    page_size: int = 20,
    supports_prop: bool = True,
) -> dict[str, Any]:
    """Lee una tabla ``kpi_*`` con filtro de fechas y devuelve el dashboard.

    Contrato idéntico a revenue/billing: resumen y serie sobre el rango
    completo, filas paginadas, ``ValueError`` para rangos invertidos y
    ``available: false`` (con ``message``) cuando ClickHouse no responde.
    """
    settings = get_settings()
    start, end = _validate_range(date_from, date_to, days)
    if page < 1 or page_size < 1:
        raise ValueError("page y page_size deben ser mayores que cero")

    try:
        import clickhouse_connect  # type: ignore

        client = clickhouse_connect.get_client(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            username=settings.clickhouse_user,
            password=settings.clickhouse_password,
            database=settings.clickhouse_database,
        )
        try:
            where = ["date >= {date_from:Date}", "date <= {date_to:Date}"]
            params: dict[str, Any] = {"date_from": start, "date_to": end}
            if prop_id is not None and supports_prop:
                where.append("prop_id = {prop_id:UInt32}")
                params["prop_id"] = prop_id
            query = (
                f"SELECT {columns} FROM {table} FINAL WHERE "
                + " AND ".join(where)
                + f" ORDER BY {order_by}"
            )
            result = client.query(query, parameters=params)
            names = [name.strip() for name in columns.split(",")]
            all_rows = [_row_to_dict(names, row) for row in result.result_rows]
            total = len(all_rows)
            page_rows = all_rows[(page - 1) * page_size : page * page_size]
            return {
                "available": True,
                "source": "clickhouse",
                "date_from": start.isoformat(),
                "date_to": end.isoformat(),
                "prop_id": prop_id,
                "summary": summary_fn(all_rows),
                "series": series_fn(all_rows),
                "rows": page_rows,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": max(1, math.ceil(total / page_size)),
                "has_next": page * page_size < total,
                "has_prev": page > 1,
            }
        finally:
            client.close()
    except Exception as exc:  # ClickHouse es opcional durante el desarrollo local.
        return {
            "available": False,
            "source": "clickhouse",
            "date_from": start.isoformat(),
            "date_to": end.isoformat(),
            "prop_id": prop_id,
            "summary": summary_fn([]),
            "series": {"labels": [], "datasets": []},
            "rows": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 1,
            "has_next": False,
            "has_prev": False,
            "message": str(exc),
        }


# ─── kpi_booking_daily ────────────────────────────────────────────────────


def get_booking_dashboard(
    *,
    prop_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    days: int = 30,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Informe de reservas por día × hotel × tipo × fuente × estado."""
    return _dashboard(
        table="kpi_booking_daily",
        columns=_BOOKING_COLUMNS,
        order_by="date ASC, prop_id ASC, room_type_id ASC, booking_source ASC, status ASC",
        summary_fn=_booking_summary,
        series_fn=_booking_series,
        prop_id=prop_id,
        date_from=date_from,
        date_to=date_to,
        days=days,
        page=page,
        page_size=page_size,
    )


def _booking_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    bookings = nights = adults = children = cancelled = 0
    revenue = 0.0
    by_status: dict[str, dict[str, Any]] = {}
    by_source: dict[str, dict[str, Any]] = {}
    by_hotel: dict[tuple[int, str], dict[str, Any]] = {}
    for row in rows:
        count = int(row.get("bookings") or 0)
        bookings += count
        nights += int(row.get("nights") or 0)
        revenue += float(row.get("revenue_usd") or 0)
        adults += int(row.get("adults") or 0)
        children += int(row.get("children") or 0)
        cancelled += int(row.get("cancelled") or 0)

        status = row.get("status") or ""
        bucket = by_status.setdefault(status, {
            "status": status,
            "label": _BOOKING_STATUS_LABELS.get(status, status or "Sin estado"),
            "bookings": 0, "revenue_usd": 0.0, "cancelled": 0,
        })
        bucket["bookings"] += count
        bucket["revenue_usd"] += float(row.get("revenue_usd") or 0)
        bucket["cancelled"] += int(row.get("cancelled") or 0)

        source = row.get("booking_source") or ""
        src = by_source.setdefault(source, {"source": source, "bookings": 0, "revenue_usd": 0.0})
        src["bookings"] += count
        src["revenue_usd"] += float(row.get("revenue_usd") or 0)

        hotel_key = (int(row.get("prop_id") or 0), row.get("hotel_label") or "")
        hotel = by_hotel.setdefault(hotel_key, {
            "prop_id": hotel_key[0], "hotel_label": hotel_key[1],
            "bookings": 0, "revenue_usd": 0.0,
        })
        hotel["bookings"] += count
        hotel["revenue_usd"] += float(row.get("revenue_usd") or 0)

    return {
        "bookings": bookings,
        "nights": nights,
        "revenue_usd": _round2(revenue),
        "adults": adults,
        "children": children,
        "cancelled": cancelled,
        "by_status": by_status,
        "by_source": sorted(by_source.values(), key=lambda item: -item["bookings"]),
        "by_hotel": sorted(by_hotel.values(), key=lambda item: -item["revenue_usd"]),
    }


def _booking_series(rows: list[dict[str, Any]]) -> dict[str, Any]:
    daily: dict[str, dict[str, float]] = {}
    for row in rows:
        day = row.get("date") or ""
        bucket = daily.setdefault(day, {"bookings": 0.0, "revenue_usd": 0.0})
        bucket["bookings"] += int(row.get("bookings") or 0)
        bucket["revenue_usd"] += float(row.get("revenue_usd") or 0)
    labels = sorted(daily)
    return {
        "labels": labels,
        "datasets": [
            {"label": "Reservas", "data": [int(daily[d]["bookings"]) for d in labels]},
            {"label": "Revenue (USD)", "data": [_round2(daily[d]["revenue_usd"]) for d in labels]},
        ],
    }


# ─── kpi_booking_nights_daily ─────────────────────────────────────────────


def get_booking_nights_dashboard(
    *,
    prop_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    days: int = 30,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Informe de ocupación real por noche de estancia (R1.x revenue)."""
    return _dashboard(
        table="kpi_booking_nights_daily",
        columns=_NIGHTS_COLUMNS,
        order_by="date ASC, prop_id ASC, room_type_id ASC, currency ASC",
        summary_fn=_nights_summary,
        series_fn=_nights_series,
        prop_id=prop_id,
        date_from=date_from,
        date_to=date_to,
        days=days,
        page=page,
        page_size=page_size,
    )


def _nights_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    rooms_sold = room_nights = cancelled_rooms = adults = children = 0
    revenue = 0.0
    by_room_type: dict[str, dict[str, Any]] = {}
    by_currency: dict[str, dict[str, Any]] = {}
    for row in rows:
        rooms_sold += int(row.get("rooms_sold") or 0)
        room_nights += int(row.get("room_nights") or 0)
        revenue += float(row.get("revenue") or 0)
        cancelled_rooms += int(row.get("cancelled_rooms") or 0)
        adults += int(row.get("adults") or 0)
        children += int(row.get("children") or 0)

        room_type_id = row.get("room_type_id") or ""
        bucket = by_room_type.setdefault(room_type_id, {
            "room_type_id": room_type_id,
            "room_type_label": row.get("room_type_label") or room_type_id,
            "room_nights": 0, "revenue": 0.0,
        })
        bucket["room_nights"] += int(row.get("room_nights") or 0)
        bucket["revenue"] += float(row.get("revenue") or 0)

        currency = row.get("currency") or ""
        curr = by_currency.setdefault(currency, {"currency": currency, "revenue": 0.0})
        curr["revenue"] += float(row.get("revenue") or 0)

    return {
        "rooms_sold": rooms_sold,
        "room_nights": room_nights,
        "revenue": _round2(revenue),
        "cancelled_rooms": cancelled_rooms,
        "adults": adults,
        "children": children,
        "by_room_type": sorted(by_room_type.values(), key=lambda item: -item["room_nights"]),
        "by_currency": sorted(by_currency.values(), key=lambda item: -item["revenue"]),
    }


def _nights_series(rows: list[dict[str, Any]]) -> dict[str, Any]:
    daily: dict[str, dict[str, float]] = {}
    for row in rows:
        day = row.get("date") or ""
        bucket = daily.setdefault(day, {"room_nights": 0.0, "revenue": 0.0})
        bucket["room_nights"] += int(row.get("room_nights") or 0)
        bucket["revenue"] += float(row.get("revenue") or 0)
    labels = sorted(daily)
    return {
        "labels": labels,
        "datasets": [
            {"label": "Noches ocupadas", "data": [int(daily[d]["room_nights"]) for d in labels]},
            {"label": "Revenue", "data": [_round2(daily[d]["revenue"]) for d in labels]},
        ],
    }


# ─── kpi_rate_daily ───────────────────────────────────────────────────────


def get_rate_dashboard(
    *,
    prop_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    days: int = 30,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Informe de tarifa publicada por día × hotel × plan (R2.x rates)."""
    return _dashboard(
        table="kpi_rate_daily",
        columns=_RATE_COLUMNS,
        order_by="date ASC, prop_id ASC, rate_plan_id ASC, room_type_id ASC",
        summary_fn=_rate_summary,
        series_fn=_rate_series,
        prop_id=prop_id,
        date_from=date_from,
        date_to=date_to,
        days=days,
        page=page,
        page_size=page_size,
    )


def _rate_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_rate = 0.0
    rated_rows = 0
    closed_days = 0
    plans: set[str] = set()
    by_rate_plan: dict[str, dict[str, Any]] = {}
    for row in rows:
        rate = float(row.get("published_rate") or 0)
        if rate > 0:
            total_rate += rate
            rated_rows += 1
        closed_days += int(row.get("closed") or 0)
        plan_id = row.get("rate_plan_id") or ""
        plans.add(plan_id)
        bucket = by_rate_plan.setdefault(plan_id, {
            "rate_plan_id": plan_id,
            "rate_plan_label": row.get("rate_plan_label") or plan_id,
            "rate_sum": 0.0, "rate_rows": 0, "closed_days": 0,
        })
        if rate > 0:
            bucket["rate_sum"] += rate
            bucket["rate_rows"] += 1
        bucket["closed_days"] += int(row.get("closed") or 0)

    return {
        "plans": len(plans),
        "avg_published_rate": _round2(total_rate / rated_rows) if rated_rows else 0.0,
        "closed_days": closed_days,
        "by_rate_plan": {
            plan_id: {
                "rate_plan_id": plan_id,
                "rate_plan_label": bucket["rate_plan_label"],
                "avg_published_rate": _round2(bucket["rate_sum"] / bucket["rate_rows"]) if bucket["rate_rows"] else 0.0,
                "closed_days": bucket["closed_days"],
            }
            for plan_id, bucket in by_rate_plan.items()
        },
    }


def _rate_series(rows: list[dict[str, Any]]) -> dict[str, Any]:
    daily: dict[str, dict[str, float]] = {}
    for row in rows:
        day = row.get("date") or ""
        bucket = daily.setdefault(day, {"rate_sum": 0.0, "rate_rows": 0.0, "closed": 0.0})
        rate = float(row.get("published_rate") or 0)
        if rate > 0:
            bucket["rate_sum"] += rate
            bucket["rate_rows"] += 1
        bucket["closed"] += int(row.get("closed") or 0)
    labels = sorted(daily)
    return {
        "labels": labels,
        "datasets": [
            {
                "label": "Tarifa media",
                "data": [
                    _round2(daily[d]["rate_sum"] / daily[d]["rate_rows"]) if daily[d]["rate_rows"] else 0
                    for d in labels
                ],
            },
            {"label": "Días cerrados", "data": [int(daily[d]["closed"]) for d in labels]},
        ],
    }


# ─── kpi_inventory_daily ──────────────────────────────────────────────────


def get_inventory_dashboard(
    *,
    prop_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    days: int = 30,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Informe de disponibilidad por día × hotel × tipo de habitación."""
    return _dashboard(
        table="kpi_inventory_daily",
        columns=_INVENTORY_COLUMNS,
        order_by="date ASC, prop_id ASC, room_type_id ASC",
        summary_fn=_inventory_summary,
        series_fn=_inventory_series,
        prop_id=prop_id,
        date_from=date_from,
        date_to=date_to,
        days=days,
        page=page,
        page_size=page_size,
    )


def _inventory_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    available = blocked = total = 0.0
    count = 0
    by_room_type: dict[str, dict[str, Any]] = {}
    by_hotel: dict[tuple[int, str], dict[str, Any]] = {}
    for row in rows:
        available += float(row.get("available_rooms") or 0)
        blocked += float(row.get("blocked_rooms") or 0)
        total += float(row.get("total_rooms") or 0)
        count += 1

        room_type_id = row.get("room_type_id") or ""
        bucket = by_room_type.setdefault(room_type_id, {
            "room_type_id": room_type_id,
            "room_type_label": row.get("room_type_label") or room_type_id,
            "available_rooms": 0.0, "blocked_rooms": 0.0, "total_rooms": 0.0,
            "days": 0,
        })
        bucket["available_rooms"] += float(row.get("available_rooms") or 0)
        bucket["blocked_rooms"] += float(row.get("blocked_rooms") or 0)
        bucket["total_rooms"] += float(row.get("total_rooms") or 0)
        bucket["days"] += 1

        hotel_key = (int(row.get("prop_id") or 0), row.get("hotel_label") or "")
        hotel = by_hotel.setdefault(hotel_key, {
            "prop_id": hotel_key[0], "hotel_label": hotel_key[1],
            "available_rooms": 0.0, "total_rooms": 0.0, "days": 0,
        })
        hotel["available_rooms"] += float(row.get("available_rooms") or 0)
        hotel["total_rooms"] += float(row.get("total_rooms") or 0)
        hotel["days"] += 1

    def _avg(value: float) -> float:
        return _round2(value / count) if count else 0.0

    return {
        "avg_available": _avg(available),
        "avg_blocked": _avg(blocked),
        "avg_total": _avg(total),
        "rows_in_range": count,
        "by_room_type": {
            rt["room_type_id"]: {
                "room_type_id": rt["room_type_id"],
                "room_type_label": rt["room_type_label"],
                "available_rooms": int(rt["available_rooms"]),
                "blocked_rooms": int(rt["blocked_rooms"]),
                "total_rooms": int(rt["total_rooms"]),
                "avg_available": _round2(rt["available_rooms"] / rt["days"]) if rt["days"] else 0.0,
                "avg_blocked": _round2(rt["blocked_rooms"] / rt["days"]) if rt["days"] else 0.0,
                "avg_total": _round2(rt["total_rooms"] / rt["days"]) if rt["days"] else 0.0,
            }
            for rt in by_room_type.values()
        },
        "by_hotel": sorted(
            (
                {
                    "prop_id": h["prop_id"],
                    "hotel_label": h["hotel_label"],
                    "avg_available": _round2(h["available_rooms"] / h["days"]) if h["days"] else 0.0,
                    "avg_total": _round2(h["total_rooms"] / h["days"]) if h["days"] else 0.0,
                }
                for h in by_hotel.values()
            ),
            key=lambda item: -item["avg_total"],
        ),
    }


def _inventory_series(rows: list[dict[str, Any]]) -> dict[str, Any]:
    daily: dict[str, dict[str, float]] = {}
    for row in rows:
        day = row.get("date") or ""
        bucket = daily.setdefault(day, {"available_rooms": 0.0, "total_rooms": 0.0, "days": 0.0})
        bucket["available_rooms"] += float(row.get("available_rooms") or 0)
        bucket["total_rooms"] += float(row.get("total_rooms") or 0)
        bucket["days"] += 1
    labels = sorted(daily)
    return {
        "labels": labels,
        "datasets": [
            {
                "label": "Disponibles",
                "data": [
                    _round2(daily[d]["available_rooms"] / daily[d]["days"]) if daily[d]["days"] else 0
                    for d in labels
                ],
            },
            {
                "label": "Totales",
                "data": [
                    _round2(daily[d]["total_rooms"] / daily[d]["days"]) if daily[d]["days"] else 0
                    for d in labels
                ],
            },
        ],
    }


# ─── kpi_funnel_daily ─────────────────────────────────────────────────────


def get_funnel_dashboard(
    *,
    prop_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    days: int = 30,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Informe global de embudo por día × país visitante × destino.

    ``kpi_funnel_daily`` no tiene ``prop_id`` (granularidad mercado/destino),
    así que el filtro por propiedad no aplica a esta tabla.
    """
    return _dashboard(
        table="kpi_funnel_daily",
        columns=_FUNNEL_COLUMNS,
        order_by="date ASC, visitor_location_country_id ASC, srch_destination_id ASC",
        summary_fn=_funnel_summary,
        series_fn=_funnel_series,
        prop_id=prop_id,
        date_from=date_from,
        date_to=date_to,
        days=days,
        page=page,
        page_size=page_size,
        supports_prop=False,
    )


def _funnel_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    searches = clicks = reservations = 0
    revenue = 0.0
    booking_window_sum = 0.0
    booking_window_rows = 0
    by_country: dict[str, dict[str, Any]] = {}
    by_destination: dict[str, dict[str, Any]] = {}
    for row in rows:
        searches += int(row.get("searches") or 0)
        clicks += int(row.get("clicks") or 0)
        reservations += int(row.get("reservations") or 0)
        revenue += float(row.get("revenue_usd") or 0)
        window = float(row.get("avg_booking_window") or 0)
        if window:
            booking_window_sum += window
            booking_window_rows += 1

        country = row.get("visitor_country_label") or str(row.get("visitor_location_country_id") or "")
        c = by_country.setdefault(country, {
            "visitor_country_label": country,
            "searches": 0, "reservations": 0, "revenue_usd": 0.0,
        })
        c["searches"] += int(row.get("searches") or 0)
        c["reservations"] += int(row.get("reservations") or 0)
        c["revenue_usd"] += float(row.get("revenue_usd") or 0)

        destination = row.get("destination_label") or str(row.get("srch_destination_id") or "")
        d = by_destination.setdefault(destination, {
            "destination_label": destination,
            "searches": 0, "reservations": 0, "revenue_usd": 0.0,
        })
        d["searches"] += int(row.get("searches") or 0)
        d["reservations"] += int(row.get("reservations") or 0)
        d["revenue_usd"] += float(row.get("revenue_usd") or 0)

    return {
        "searches": searches,
        "clicks": clicks,
        "reservations": reservations,
        "revenue_usd": _round2(revenue),
        "conversion_percent": round((reservations / searches) * 100, 2) if searches else 0.0,
        "avg_booking_window": round(booking_window_sum / booking_window_rows, 2) if booking_window_rows else 0.0,
        "by_country": sorted(by_country.values(), key=lambda item: -item["searches"]),
        "by_destination": sorted(by_destination.values(), key=lambda item: -item["searches"]),
    }


def _funnel_series(rows: list[dict[str, Any]]) -> dict[str, Any]:
    daily: dict[str, dict[str, float]] = {}
    for row in rows:
        day = row.get("date") or ""
        bucket = daily.setdefault(day, {"searches": 0.0, "reservations": 0.0})
        bucket["searches"] += int(row.get("searches") or 0)
        bucket["reservations"] += int(row.get("reservations") or 0)
    labels = sorted(daily)
    return {
        "labels": labels,
        "datasets": [
            {"label": "Búsquedas", "data": [int(daily[d]["searches"]) for d in labels]},
            {"label": "Reservas", "data": [int(daily[d]["reservations"]) for d in labels]},
        ],
    }


# ─── kpi_funnel_property_channel_daily ────────────────────────────────────


def get_funnel_property_channel_dashboard(
    *,
    prop_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    days: int = 30,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Informe de embudo por hotel buscado × canal × mercado × destino."""
    return _dashboard(
        table="kpi_funnel_property_channel_daily",
        columns=_FUNNEL_PC_COLUMNS,
        order_by="date ASC, prop_id ASC, site_id ASC, visitor_location_country_id ASC, srch_destination_id ASC",
        summary_fn=_funnel_pc_summary,
        series_fn=_funnel_series,
        prop_id=prop_id,
        date_from=date_from,
        date_to=date_to,
        days=days,
        page=page,
        page_size=page_size,
    )


def _funnel_pc_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    searches = clicks = reservations = adults = children = rooms = 0
    revenue = 0.0
    booking_window_sum = 0.0
    length_sum = 0.0
    metric_rows = 0
    by_site: dict[str, dict[str, Any]] = {}
    by_hotel: dict[tuple[int, str], dict[str, Any]] = {}
    for row in rows:
        searches += int(row.get("searches") or 0)
        clicks += int(row.get("clicks") or 0)
        reservations += int(row.get("reservations") or 0)
        revenue += float(row.get("revenue_usd") or 0)
        adults += int(row.get("adults") or 0)
        children += int(row.get("children") or 0)
        rooms += int(row.get("rooms") or 0)
        if float(row.get("avg_booking_window") or 0) or float(row.get("avg_length_of_stay") or 0):
            booking_window_sum += float(row.get("avg_booking_window") or 0)
            length_sum += float(row.get("avg_length_of_stay") or 0)
            metric_rows += 1

        site = row.get("site_label") or str(row.get("site_id") or "")
        s = by_site.setdefault(site, {
            "site_label": site, "searches": 0, "reservations": 0, "revenue_usd": 0.0,
        })
        s["searches"] += int(row.get("searches") or 0)
        s["reservations"] += int(row.get("reservations") or 0)
        s["revenue_usd"] += float(row.get("revenue_usd") or 0)

        hotel_key = (int(row.get("prop_id") or 0), row.get("hotel_label") or "")
        h = by_hotel.setdefault(hotel_key, {
            "prop_id": hotel_key[0], "hotel_label": hotel_key[1],
            "searches": 0, "reservations": 0, "revenue_usd": 0.0,
        })
        h["searches"] += int(row.get("searches") or 0)
        h["reservations"] += int(row.get("reservations") or 0)
        h["revenue_usd"] += float(row.get("revenue_usd") or 0)

    return {
        "searches": searches,
        "clicks": clicks,
        "reservations": reservations,
        "revenue_usd": _round2(revenue),
        "conversion_percent": round((reservations / searches) * 100, 2) if searches else 0.0,
        "avg_booking_window": round(booking_window_sum / metric_rows, 2) if metric_rows else 0.0,
        "avg_length_of_stay": round(length_sum / metric_rows, 2) if metric_rows else 0.0,
        "adults": adults,
        "children": children,
        "rooms": rooms,
        "by_site": sorted(by_site.values(), key=lambda item: -item["searches"]),
        "by_hotel": sorted(by_hotel.values(), key=lambda item: -item["searches"]),
    }
