"""Transformación: mapeo de documentos MongoDB a filas columnar ClickHouse.

Contrato de FASE 1. Implementación en FASE 2.
"""

from __future__ import annotations

from typing import Any

# Orden de columnas y tipos ClickHouse por tabla (contrato con load.py).
TABLE_COLUMNS: dict[str, list[str]] = {
    "kpi_booking_daily": [
        "date",
        "prop_id",
        "hotel_label",
        "room_type_id",
        "room_type_label",
        "booking_source",
        "status",
        "bookings",
        "nights",
        "revenue_usd",
        "adults",
        "children",
        "cancelled",
    ],
    "kpi_booking_nights_daily": [
        "date", "prop_id", "hotel_label", "room_type_id", "room_type_label", "currency", "rooms_sold", "room_nights",
        "revenue", "cancelled_rooms", "adults", "children",
    ],
    "kpi_inventory_daily": [
        "date", "prop_id", "hotel_label", "room_type_id", "room_type_label", "available_rooms", "blocked_rooms", "total_rooms",
    ],
    "kpi_rate_daily": [
        "date", "prop_id", "hotel_label", "rate_plan_id", "rate_plan_label", "room_type_id", "room_type_label", "currency", "published_rate", "closed",
    ],
    "kpi_room_performance_daily": [
        "date", "prop_id", "hotel_label", "room_type_id", "room_type_label", "currency", "booking_source", "rooms_sold", "room_nights", "revenue",
        "cancelled_rooms", "available_rooms", "blocked_rooms", "total_rooms", "published_rate", "rate_variance",
    ],
    "kpi_review_daily": [
        "date", "prop_id", "hotel_label", "reviews", "rating_sum", "avg_rating", "approved", "pending", "rejected",
        "responded", "positive", "neutral", "negative", "moderated_count", "avg_moderation_minutes",
        "responded_count", "avg_response_minutes",
    ],
    "kpi_funnel_daily": [
        "date",
        "visitor_location_country_id",
        "visitor_country_label",
        "srch_destination_id",
        "destination_label",
        "searches",
        "clicks",
        "reservations",
        "revenue_usd",
        "avg_booking_window",
    ],
    "kpi_funnel_property_channel_daily": [
        "date",
        "prop_id",
        "hotel_label",
        "site_id",
        "site_label",
        "visitor_location_country_id",
        "visitor_country_label",
        "srch_destination_id",
        "destination_label",
        "searches",
        "clicks",
        "reservations",
        "revenue_usd",
        "avg_booking_window",
        "avg_length_of_stay",
        "adults",
        "children",
        "rooms",
    ],
    "kpi_housekeeping_daily": [
        "date", "prop_id", "hotel_label", "tasks_total", "tasks_completed",
        "tasks_completed_on_time", "tasks_with_completed_at", "maintenance_total",
        "maintenance_completed", "maintenance_completed_on_time", "rooms_status_events",
        "rooms_to_clean", "rooms_cleaned", "rooms_available_after_cleaning",
        "avg_cleaning_minutes", "avg_checkout_to_available_minutes", "rotation_observed",
        "inventory_available_rooms", "inventory_blocked_rooms", "inventory_total_rooms",
        "charges_total", "charges_amount", "supplier_country_coverage",
    ],
    "kpi_invoice_daily": [
        "date", "prop_id", "hotel_label", "status", "invoice_count",
        "subtotal", "taxes", "total", "paid_total", "pending_total",
        "cancelled_total",
    ],
    "kpi_payment_daily": [
        "date", "prop_id", "hotel_label", "method", "status", "payment_count",
        "paid_amount", "refunded_amount", "failed_amount", "invoiced_amount",
        "collected_amount", "outstanding_amount",
    ],
    # ── Capa estratégica mensual (TAF14) ────────────────────────────────
    "strat_hotel_monthly": [
        "month", "prop_id", "hotel_label", "currency", "bookings", "rooms_sold",
        "room_nights", "revenue", "discount_amount", "adults", "children",
        "cancelled_rooms", "total_rooms", "city", "city_lat", "city_lng",
    ],
    "strat_plan_monthly": [
        "month", "prop_id", "hotel_label", "room_type_id", "room_type_label", "currency",
        "bookings", "rooms_sold", "room_nights", "revenue", "discount_amount",
        "adults", "children", "cancelled_rooms",
    ],
    "strat_market_monthly": [
        "month", "visitor_location_country_id", "visitor_country_label",
        "srch_destination_id", "destination_label", "searches", "clicks",
        "reservations", "revenue_usd",
    ],
    "strat_reputation_monthly": [
        "month", "prop_id", "hotel_label", "reviews", "avg_rating", "positive",
        "neutral", "negative", "responded", "response_rate",
    ],
}


class _NotGiven:
    pass


_NOT_GIVEN = _NotGiven()


def _pick(doc: dict[str, Any], *names: str, default: Any = _NOT_GIVEN) -> Any:
    """Primer campo presente entre ``names`` (soporta alias de mongo)."""
    for name in names:
        if name in doc and doc[name] is not None:
            return doc[name]
    if default is not _NOT_GIVEN:
        return default
    return None


def _as_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _as_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_datetime(value: Any) -> Any:
    from datetime import datetime as _datetime
    if isinstance(value, _datetime):
        return value
    text = _as_str(value).replace("Z", "+00:00")
    try:
        return _datetime.fromisoformat(text)
    except ValueError:
        return None


def _as_date(value: Any, default: str = "") -> Any:
    """Convierte a ``datetime.date`` para columnas ClickHouse tipo Date.

    Devuelve ``None`` cuando el valor no es una fecha válida; la guarda de
    ``transform_rows_with_stats`` descarta esas filas antes del load, así que
    nunca llega un 1970-01-01 ficticio a ClickHouse.
    """
    from datetime import date as _date
    from datetime import datetime as _datetime

    if isinstance(value, _datetime):
        return value.date()
    if isinstance(value, _date):
        return value
    text = _as_str(value, default).split("T")[0]
    if len(text) == 8 and text.isdigit():
        text = f"{text[:4]}-{text[4:6]}-{text[6:]}"
    try:
        return _date.fromisoformat(text)
    except ValueError:
        return None


def _kpi_booking_daily(doc: dict[str, Any]) -> list[Any]:
    return [
        _as_date(doc.get("date")),
        _as_int(doc.get("prop_id")),
        _as_str(doc.get("hotel_label")),
        _as_str(doc.get("room_type_id")),
        _as_str(doc.get("room_type_label")),
        _as_str(doc.get("booking_source")),
        _as_str(doc.get("status")),
        _as_int(doc.get("bookings")),
        _as_int(doc.get("nights")),
        _as_float(doc.get("revenue_usd")),
        _as_int(doc.get("adults")),
        _as_int(doc.get("children")),
        _as_int(doc.get("cancelled")),
    ]


def _kpi_booking_nights_daily(doc: dict[str, Any]) -> list[Any]:
    return [_as_date(doc.get("date")), _as_int(doc.get("prop_id")), _as_str(doc.get("hotel_label")), _as_str(doc.get("room_type_id")), _as_str(doc.get("room_type_label")), _as_str(doc.get("currency")), _as_int(doc.get("rooms_sold")), _as_int(doc.get("room_nights")), _as_float(doc.get("revenue")), _as_int(doc.get("cancelled_rooms")), _as_int(doc.get("adults")), _as_int(doc.get("children"))]


def _kpi_inventory_daily(doc: dict[str, Any]) -> list[Any]:
    return [_as_date(doc.get("date")), _as_int(doc.get("prop_id")), _as_str(doc.get("hotel_label")), _as_str(doc.get("room_type_id")), _as_str(doc.get("room_type_label")), _as_int(doc.get("available_rooms")), _as_int(doc.get("blocked_rooms")), _as_int(doc.get("total_rooms"))]


def _kpi_rate_daily(doc: dict[str, Any]) -> list[Any]:
    return [_as_date(doc.get("date")), _as_int(doc.get("prop_id")), _as_str(doc.get("hotel_label")), _as_str(doc.get("rate_plan_id")), _as_str(doc.get("rate_plan_label")), _as_str(doc.get("room_type_id")), _as_str(doc.get("room_type_label")), _as_str(doc.get("currency")), _as_float(doc.get("published_rate")), _as_bool(doc.get("closed"))]


def _kpi_room_performance_daily(doc: dict[str, Any]) -> list[Any]:
    return [_as_date(doc.get("date")), _as_int(doc.get("prop_id")), _as_str(doc.get("hotel_label")), _as_str(doc.get("room_type_id")), _as_str(doc.get("room_type_label")), _as_str(doc.get("currency")), _as_str(doc.get("booking_source")), _as_int(doc.get("rooms_sold")), _as_int(doc.get("room_nights")), _as_float(doc.get("revenue")), _as_int(doc.get("cancelled_rooms")), _as_int(doc.get("available_rooms")), _as_int(doc.get("blocked_rooms")), _as_int(doc.get("total_rooms")), None if doc.get("published_rate") is None else _as_float(doc.get("published_rate")), None if doc.get("rate_variance") is None else _as_float(doc.get("rate_variance"))]


def _kpi_review_daily(doc: dict[str, Any]) -> list[Any]:
    return [
        _as_date(doc.get("date")), _as_int(doc.get("prop_id")), _as_str(doc.get("hotel_label")), _as_int(doc.get("reviews")),
        _as_float(doc.get("rating_sum")), _as_float(doc.get("avg_rating")), _as_int(doc.get("approved")),
        _as_int(doc.get("pending")), _as_int(doc.get("rejected")), _as_int(doc.get("responded")),
        _as_int(doc.get("positive")), _as_int(doc.get("neutral")), _as_int(doc.get("negative")),
        _as_int(doc.get("moderated_count")), None if doc.get("avg_moderation_minutes") is None else _as_float(doc.get("avg_moderation_minutes")),
        _as_int(doc.get("responded_count")), None if doc.get("avg_response_minutes") is None else _as_float(doc.get("avg_response_minutes")),
    ]


def _kpi_funnel_daily(doc: dict[str, Any]) -> list[Any]:
    return [
        _as_date(doc.get("date")),
        _as_int(doc.get("visitor_location_country_id")),
        _as_str(doc.get("visitor_country_label")),
        _as_int(doc.get("srch_destination_id")),
        _as_str(doc.get("destination_label")),
        _as_int(doc.get("searches")),
        _as_int(doc.get("clicks")),
        _as_int(doc.get("reservations")),
        _as_float(doc.get("revenue_usd")),
        _as_float(doc.get("avg_booking_window")),
    ]


def _kpi_funnel_property_channel_daily(doc: dict[str, Any]) -> list[Any]:
    return [
        _as_date(doc.get("date")),
        _as_int(doc.get("prop_id")),
        _as_str(doc.get("hotel_label")),
        _as_int(doc.get("site_id")),
        _as_str(doc.get("site_label")),
        _as_int(doc.get("visitor_location_country_id")),
        _as_str(doc.get("visitor_country_label")),
        _as_int(doc.get("srch_destination_id")),
        _as_str(doc.get("destination_label")),
        _as_int(doc.get("searches")),
        _as_int(doc.get("clicks")),
        _as_int(doc.get("reservations")),
        _as_float(doc.get("revenue_usd")),
        _as_float(doc.get("avg_booking_window")),
        _as_float(doc.get("avg_length_of_stay")),
        _as_int(doc.get("adults")),
        _as_int(doc.get("children")),
        _as_int(doc.get("rooms")),
    ]


def _nullable_float(doc: dict[str, Any], key: str) -> float | None:
    return None if doc.get(key) is None else _as_float(doc.get(key))


def _strat_hotel_monthly(doc: dict[str, Any]) -> list[Any]:
    return [
        _as_date(doc.get("month")),
        _as_int(doc.get("prop_id")),
        _as_str(doc.get("hotel_label")),
        _as_str(doc.get("currency")),
        _as_int(doc.get("bookings")),
        _as_int(doc.get("rooms_sold")),
        _as_int(doc.get("room_nights")),
        _as_float(doc.get("revenue")),
        _as_float(doc.get("discount_amount")),
        _as_int(doc.get("adults")),
        _as_int(doc.get("children")),
        _as_int(doc.get("cancelled_rooms")),
        _as_int(doc.get("total_rooms")),
        _as_str(doc.get("city")),
        _nullable_float(doc, "city_lat"),
        _nullable_float(doc, "city_lng"),
    ]


def _strat_plan_monthly(doc: dict[str, Any]) -> list[Any]:
    return [
        _as_date(doc.get("month")),
        _as_int(doc.get("prop_id")),
        _as_str(doc.get("hotel_label")),
        _as_str(doc.get("room_type_id")),
        _as_str(doc.get("room_type_label")),
        _as_str(doc.get("currency")),
        _as_int(doc.get("bookings")),
        _as_int(doc.get("rooms_sold")),
        _as_int(doc.get("room_nights")),
        _as_float(doc.get("revenue")),
        _as_float(doc.get("discount_amount")),
        _as_int(doc.get("adults")),
        _as_int(doc.get("children")),
        _as_int(doc.get("cancelled_rooms")),
    ]


def _strat_market_monthly(doc: dict[str, Any]) -> list[Any]:
    return [
        _as_date(doc.get("month")),
        _as_int(doc.get("visitor_location_country_id")),
        _as_str(doc.get("visitor_country_label")),
        _as_int(doc.get("srch_destination_id")),
        _as_str(doc.get("destination_label")),
        _as_int(doc.get("searches")),
        _as_int(doc.get("clicks")),
        _as_int(doc.get("reservations")),
        _as_float(doc.get("revenue_usd")),
    ]


def _strat_reputation_monthly(doc: dict[str, Any]) -> list[Any]:
    return [
        _as_date(doc.get("month")),
        _as_int(doc.get("prop_id")),
        _as_str(doc.get("hotel_label")),
        _as_int(doc.get("reviews")),
        _as_float(doc.get("avg_rating")),
        _as_int(doc.get("positive")),
        _as_int(doc.get("neutral")),
        _as_int(doc.get("negative")),
        _as_int(doc.get("responded")),
        _as_float(doc.get("response_rate")),
    ]


def _kpi_housekeeping_daily(doc: dict[str, Any]) -> list[Any]:
    return [
        _as_date(doc.get("date")), _as_int(doc.get("prop_id")), _as_str(doc.get("hotel_label")),
        _as_int(doc.get("tasks_total")), _as_int(doc.get("tasks_completed")),
        _as_int(doc.get("tasks_completed_on_time")), _as_int(doc.get("tasks_with_completed_at")),
        _as_int(doc.get("maintenance_total")), _as_int(doc.get("maintenance_completed")),
        _as_int(doc.get("maintenance_completed_on_time")), _as_int(doc.get("rooms_status_events")),
        _as_int(doc.get("rooms_to_clean")), _as_int(doc.get("rooms_cleaned")),
        _as_int(doc.get("rooms_available_after_cleaning")), _nullable_float(doc, "avg_cleaning_minutes"),
        _nullable_float(doc, "avg_checkout_to_available_minutes"), _as_int(doc.get("rotation_observed")),
        _as_int(doc.get("inventory_available_rooms")), _as_int(doc.get("inventory_blocked_rooms")),
        _as_int(doc.get("inventory_total_rooms")), _as_int(doc.get("charges_total")),
        _as_float(doc.get("charges_amount")), _as_int(doc.get("supplier_country_coverage")),
    ]


def _kpi_invoice_daily(doc: dict[str, Any]) -> list[Any]:
    return [
        _as_date(doc.get("date")),
        _as_int(doc.get("prop_id")),
        _as_str(doc.get("hotel_label")),
        _as_str(doc.get("status")),
        _as_int(doc.get("invoice_count")),
        _as_float(doc.get("subtotal")),
        _as_float(doc.get("taxes")),
        _as_float(doc.get("total")),
        _as_float(doc.get("paid_total")),
        _as_float(doc.get("pending_total")),
        _as_float(doc.get("cancelled_total")),
    ]


def _kpi_payment_daily(doc: dict[str, Any]) -> list[Any]:
    return [
        _as_date(doc.get("date")),
        _as_int(doc.get("prop_id")),
        _as_str(doc.get("hotel_label")),
        _as_str(doc.get("method")),
        _as_str(doc.get("status")),
        _as_int(doc.get("payment_count")),
        _as_float(doc.get("paid_amount")),
        _as_float(doc.get("refunded_amount")),
        _as_float(doc.get("failed_amount")),
        _as_float(doc.get("invoiced_amount")),
        _as_float(doc.get("collected_amount")),
        _as_float(doc.get("outstanding_amount")),
    ]


_MAPPERS = {
    "kpi_booking_daily": _kpi_booking_daily,
    "kpi_booking_nights_daily": _kpi_booking_nights_daily,
    "kpi_inventory_daily": _kpi_inventory_daily,
    "kpi_rate_daily": _kpi_rate_daily,
    "kpi_room_performance_daily": _kpi_room_performance_daily,
    "kpi_review_daily": _kpi_review_daily,
    "kpi_funnel_daily": _kpi_funnel_daily,
    "kpi_funnel_property_channel_daily": _kpi_funnel_property_channel_daily,
    "kpi_housekeeping_daily": _kpi_housekeeping_daily,
    "kpi_invoice_daily": _kpi_invoice_daily,
    "kpi_payment_daily": _kpi_payment_daily,
    "strat_hotel_monthly": _strat_hotel_monthly,
    "strat_plan_monthly": _strat_plan_monthly,
    "strat_market_monthly": _strat_market_monthly,
    "strat_reputation_monthly": _strat_reputation_monthly,
}


def transform_rows_with_stats(
    table_name: str, raw_docs: list[dict[str, Any]]
) -> tuple[list[list[Any]], int]:
    """Mapea documentos y descarta filas sin fecha válida.

    La primera columna de toda tabla es su columna de fecha (``date`` en la
    capa táctica, ``month`` en la estratégica). Si el mapper devuelve ``None``
    en esa posición (fecha vacía o ilegible), la fila se descarta y se cuenta
    en el segundo valor de retorno para el reporte de calidad
    (``discarded_reason: invalid_date``).
    """
    mapper = _MAPPERS.get(table_name)
    if mapper is None:
        raise ValueError(f"Tabla sin mapper definido: {table_name}")
    rows: list[list[Any]] = []
    discarded = 0
    for doc in raw_docs:
        row = mapper(doc)
        if row[0] is None:
            discarded += 1
            continue
        rows.append(row)
    return rows, discarded


def transform_rows(table_name: str, raw_docs: list[dict[str, Any]]) -> list[list[Any]]:
    """Mapea documentos crudos de Mongo a filas posicionales para ClickHouse.

    Devuelve listas alineadas con ``TABLE_COLUMNS[table_name]`` (mismos tipos
    que el CREATE TABLE de ``load.py``). Las filas sin fecha válida se
    descartan (ver ``transform_rows_with_stats`` para obtener el conteo).
    """
    rows, _ = transform_rows_with_stats(table_name, raw_docs)
    return rows
