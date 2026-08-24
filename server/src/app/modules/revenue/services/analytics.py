"""Read-only tactical revenue analytics from ClickHouse (R1.2).

El dashboard de ADR consulta únicamente ``kpi_room_performance_daily``
(agregado por día × hotel × tipo de habitación × divisa × canal). Nunca lee
Mongo como sustituto ni replica reservas.
"""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone
from typing import Any

from config.settings import get_settings

_COLUMNS = (
    "date, prop_id, hotel_label, room_type_id, room_type_label, currency, "
    "booking_source, rooms_sold, room_nights, revenue, cancelled_rooms, "
    "available_rooms, blocked_rooms, total_rooms, published_rate, rate_variance"
)

_CHANNEL_LABELS: dict[str, str] = {
    "direct": "Directo",
    "direct_website": "Web directa",
    "booking_engine": "Motor de reservas",
    "ota": "OTA",
    "booking.com": "Booking.com",
    "expedia": "Expedia",
    "gds": "GDS",
    "walk_in": "Walk-in",
    "phone": "Teléfono",
    "corporate": "Corporativo",
    "agency": "Agencia",
    "tour_operator": "Tour operador",
    "": "Sin canal",
}

_ROOM_TYPE_PREFIX = "RT-"


def _default_range(days: int) -> tuple[date, date]:
    end = datetime.now(timezone.utc).date()
    return end - timedelta(days=days - 1), end


def get_room_performance_dashboard(
    *,
    prop_id: int | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    days: int = 30,
    room_type_id: str | None = None,
    channel: str | None = None,
    only_profitable: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Lee ``kpi_room_performance_daily`` y devuelve resumen + serie + filas.

    El resumen y la serie reflejan SIEMPRE el rango completo; los filtros por
    tipo de habitación, canal y "solo con ganancias" solo afectan la grilla
    (mismo criterio que el dashboard F1.4). La paginación se aplica en Python
    porque la granularidad (día × hotel × tipo × divisa × canal) mantiene el
    resultado pequeño.
    """
    settings = get_settings()
    fallback_from, fallback_to = _default_range(days)
    start = date.fromisoformat(date_from) if date_from else fallback_from
    end = date.fromisoformat(date_to) if date_to else fallback_to
    if end < start:
        raise ValueError("date_to debe ser igual o posterior a date_from")
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
            if prop_id is not None:
                where.append("prop_id = {prop_id:UInt32}")
                params["prop_id"] = prop_id
            query = (
                f"SELECT {_COLUMNS} FROM kpi_room_performance_daily FINAL WHERE "
                + " AND ".join(where)
                + " ORDER BY date ASC, prop_id ASC, room_type_id ASC, "
                + "currency ASC, booking_source ASC"
            )
            result = client.query(query, parameters=params)
            all_rows = [_row_to_dict(row) for row in result.result_rows]
            # Filtros de detalle aplican solo a la grilla, no a KPIs ni serie.
            grid_rows = [
                row
                for row in all_rows
                if (not room_type_id or row["room_type_id"] == room_type_id)
                and (not channel or row["booking_source"] == channel)
                and (not only_profitable or float(row.get("revenue") or 0) > 0)
            ]
            total = len(grid_rows)
            page_rows = grid_rows[(page - 1) * page_size : page * page_size]
            return {
                "available": True,
                "source": "clickhouse",
                "date_from": start.isoformat(),
                "date_to": end.isoformat(),
                "prop_id": prop_id,
                "summary": _summarise(all_rows, start, end),
                "series": _series(all_rows),
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
            "summary": _summarise([], start, end),
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


def _row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    names = [name.strip() for name in _COLUMNS.split(",")]
    return {
        name: (value.isoformat() if hasattr(value, "isoformat") else value)
        for name, value in zip(names, row)
    }


def _round(value: float) -> float:
    return round(float(value or 0), 2)


def _short_room_type(room_type_id: str) -> str:
    """Recorta el prefijo ``RT-{prop_id}-`` del ID para mostrar el tipo corto."""
    if not room_type_id:
        return ""
    if room_type_id.startswith(_ROOM_TYPE_PREFIX):
        parts = room_type_id.split("-")
        if len(parts) >= 3:
            return "-".join(parts[2:])
    return room_type_id


def _summarise(
    rows: list[dict[str, Any]],
    start: date,
    end: date,
) -> dict[str, Any]:
    """Agrega ADR, RevPAR, ocupación, revenue y desglose por tipo/canal.

    ADR = revenue / room_nights. RevPAR = revenue / (total_rooms × días del
    rango). Ocupación = room_nights / (total_rooms × días). El denominador usa
    la suma de habitaciones disponibles publicadas por día/tipo; cuando una
    fecha no tiene inventario publicado, sus noches no entran al denominador
    (para no fabricar una ocupación falsa).
    """
    room_nights = 0
    revenue = 0.0
    cancelled_rooms = 0
    sold = 0
    capacity_nights: dict[tuple[str, int, str], int] = {}
    by_room_type: dict[str, dict[str, Any]] = {}
    by_channel: dict[str, dict[str, Any]] = {}
    by_hotel: dict[tuple[int, str], dict[str, Any]] = {}
    has_revenue = False
    has_inventory = False

    for row in rows:
        sold += int(row.get("rooms_sold") or 0)
        room_nights += int(row.get("room_nights") or 0)
        revenue += float(row.get("revenue") or 0)
        cancelled_rooms += int(row.get("cancelled_rooms") or 0)
        if float(row.get("revenue") or 0):
            has_revenue = True
        total_rooms = int(row.get("total_rooms") or 0)
        if total_rooms:
            has_inventory = True
            # Una fila de inventario representa un día de capacidad; contar por
            # clave (fecha, prop, tipo) evita duplicar por divisa/canal.
            capacity_key = (row.get("date") or "", int(row.get("prop_id") or 0), row.get("room_type_id") or "")
            capacity_nights[capacity_key] = total_rooms

        room_type_id = row.get("room_type_id") or ""
        rbucket = by_room_type.setdefault(room_type_id, {
            "room_type_id": room_type_id,
            "room_type_label": row.get("room_type_label") or _short_room_type(room_type_id),
            "room_nights": 0, "revenue": 0.0, "cancelled_rooms": 0,
        })
        rbucket["room_nights"] += int(row.get("room_nights") or 0)
        rbucket["revenue"] += float(row.get("revenue") or 0)
        rbucket["cancelled_rooms"] += int(row.get("cancelled_rooms") or 0)

        channel = row.get("booking_source") or ""
        cbucket = by_channel.setdefault(channel, {
            "channel": channel,
            "label": _CHANNEL_LABELS.get(channel, channel or "Sin canal"),
            "room_nights": 0, "revenue": 0.0, "adr": 0.0,
        })
        cbucket["room_nights"] += int(row.get("room_nights") or 0)
        cbucket["revenue"] += float(row.get("revenue") or 0)

        hotel_key = (int(row.get("prop_id") or 0), row.get("hotel_label") or "")
        hotel = by_hotel.setdefault(hotel_key, {
            "prop_id": hotel_key[0], "hotel_label": hotel_key[1],
            "room_nights": 0, "revenue": 0.0,
        })
        hotel["room_nights"] += int(row.get("room_nights") or 0)
        hotel["revenue"] += float(row.get("revenue") or 0)

    capacity_sum = sum(capacity_nights.values())
    range_days = max(1, (end - start).days + 1)
    adr = revenue / room_nights if room_nights else 0.0
    revpar = revenue / (capacity_sum or 1)
    occupancy = (room_nights / capacity_sum) if capacity_sum else 0.0

    channels = sorted(
        ({"channel": c["channel"], "label": c["label"],
          "room_nights": c["room_nights"], "revenue": _round(c["revenue"]),
          "adr": _round(c["revenue"] / c["room_nights"]) if c["room_nights"] else 0.0}
         for c in by_channel.values()),
        key=lambda item: item["revenue"],
        reverse=True,
    )

    return {
        "adr": _round(adr),
        "revpar": _round(revpar),
        "occupancy": round(occupancy * 100, 2),
        "revenue": _round(revenue),
        "room_nights": room_nights,
        "rooms_sold": sold,
        "cancelled_rooms": cancelled_rooms,
        "capacity_nights": capacity_sum,
        "range_days": range_days,
        "has_revenue": has_revenue,
        "has_inventory": has_inventory,
        "by_room_type": sorted(
            ({"room_type_id": rt["room_type_id"], "room_type_label": rt["room_type_label"],
              "room_nights": rt["room_nights"], "revenue": _round(rt["revenue"]),
              "cancelled_rooms": rt["cancelled_rooms"],
              "adr": _round(rt["revenue"] / rt["room_nights"]) if rt["room_nights"] else 0.0}
             for rt in by_room_type.values()),
            key=lambda item: item["revenue"],
            reverse=True,
        ),
        "by_channel": channels,
        "by_hotel": sorted(
            ({"prop_id": h["prop_id"], "hotel_label": h["hotel_label"],
              "room_nights": h["room_nights"], "revenue": _round(h["revenue"]),
              "adr": _round(h["revenue"] / h["room_nights"]) if h["room_nights"] else 0.0}
             for h in by_hotel.values()),
            key=lambda item: item["revenue"],
            reverse=True,
        ),
    }


def _series(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Evolución diaria del ADR y del revenue realizado por noche de estancia."""
    daily: dict[str, dict[str, float]] = {}
    for row in rows:
        day = row.get("date") or ""
        bucket = daily.setdefault(day, {"revenue": 0.0, "room_nights": 0})
        bucket["revenue"] += float(row.get("revenue") or 0)
        bucket["room_nights"] += int(row.get("room_nights") or 0)
    labels = sorted(daily)
    return {
        "labels": labels,
        "datasets": [
            {
                "label": "ADR",
                "data": [
                    _round(daily[d]["revenue"] / daily[d]["room_nights"]) if daily[d]["room_nights"] else 0
                    for d in labels
                ],
            },
            {
                "label": "Revenue",
                "data": [_round(daily[d]["revenue"]) for d in labels],
            },
        ],
    }
