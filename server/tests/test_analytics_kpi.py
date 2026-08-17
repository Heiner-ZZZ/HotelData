"""Tests de los informes compuestos TA12 sobre tablas ``kpi_*`` (ClickHouse).

Cubren las funciones puras de resumen/serie de cada dashboard (sin depender de
ClickHouse levantado) y la validación de rango. La conectividad real se verifica
con pruebas de integración contra las tablas cargadas (se saltan si CH no está).
"""

from __future__ import annotations

import pytest


def _booking_row(
    date: str, prop: int, hotel: str, source: str, status: str,
    bookings: int, nights: int, revenue: float, cancelled: int = 0,
    adults: int = 0, children: int = 0,
) -> dict:
    return {
        "date": date, "prop_id": prop, "hotel_label": hotel,
        "room_type_id": "RT-1", "room_type_label": "Estándar",
        "booking_source": source, "status": status, "bookings": bookings,
        "nights": nights, "revenue_usd": revenue, "adults": adults,
        "children": children, "cancelled": cancelled,
    }


def test_booking_summary_aggregates_by_status_source_and_hotel():
    from src.app.modules.analytics.kpi_reports import _booking_summary

    rows = [
        _booking_row("2026-08-01", 1, "Hotel A", "direct", "confirmed", 2, 4, 200.0, adults=2),
        _booking_row("2026-08-01", 1, "Hotel A", "ota", "cancelled", 1, 2, 50.0, cancelled=1),
        _booking_row("2026-08-02", 2, "Hotel B", "direct", "confirmed", 1, 1, 100.0),
    ]
    s = _booking_summary(rows)
    assert s["bookings"] == 4
    assert s["nights"] == 7
    assert s["revenue_usd"] == 350.0
    assert s["cancelled"] == 1
    assert s["adults"] == 2
    assert s["by_status"]["confirmed"]["bookings"] == 3
    assert s["by_status"]["cancelled"]["label"] == "Cancelada"
    assert [h["hotel_label"] for h in s["by_hotel"]] == ["Hotel A", "Hotel B"]
    assert s["by_source"][0]["source"] == "direct"


def test_booking_summary_empty_returns_zeros():
    from src.app.modules.analytics.kpi_reports import _booking_summary

    s = _booking_summary([])
    assert s["bookings"] == 0
    assert s["revenue_usd"] == 0.0
    assert s["by_status"] == {}
    assert s["by_hotel"] == []


def test_booking_series_daily_bookings_and_revenue():
    from src.app.modules.analytics.kpi_reports import _booking_series

    rows = [
        _booking_row("2026-08-01", 1, "Hotel A", "direct", "confirmed", 2, 4, 200.0),
        _booking_row("2026-08-02", 2, "Hotel B", "direct", "confirmed", 1, 1, 100.0),
    ]
    series = _booking_series(rows)
    assert series["labels"] == ["2026-08-01", "2026-08-02"]
    datasets = {d["label"]: d["data"] for d in series["datasets"]}
    assert datasets["Reservas"] == [2, 1]
    assert datasets["Revenue (USD)"] == [200.0, 100.0]


def test_nights_summary_totals_and_by_room_type():
    from src.app.modules.analytics.kpi_reports import _nights_summary

    rows = [
        {"date": "2026-08-01", "prop_id": 1, "hotel_label": "Hotel A",
         "room_type_id": "RT-1", "room_type_label": "Estándar", "currency": "USD",
         "rooms_sold": 2, "room_nights": 4, "revenue": 200.0, "cancelled_rooms": 0,
         "adults": 2, "children": 1},
        {"date": "2026-08-01", "prop_id": 1, "hotel_label": "Hotel A",
         "room_type_id": "RT-2", "room_type_label": "Suite", "currency": "USD",
         "rooms_sold": 1, "room_nights": 1, "revenue": 100.0, "cancelled_rooms": 1,
         "adults": 1, "children": 0},
    ]
    s = _nights_summary(rows)
    assert s["rooms_sold"] == 3
    assert s["room_nights"] == 5
    assert s["revenue"] == 300.0
    assert s["cancelled_rooms"] == 1
    assert s["adults"] == 3
    assert s["children"] == 1
    assert [rt["room_type_id"] for rt in s["by_room_type"]] == ["RT-1", "RT-2"]


def test_rate_summary_average_and_closed_days():
    from src.app.modules.analytics.kpi_reports import _rate_summary

    rows = [
        {"date": "2026-08-01", "prop_id": 1, "hotel_label": "Hotel A",
         "rate_plan_id": "PLAN-1", "rate_plan_label": "Estándar",
         "room_type_id": "RT-1", "room_type_label": "Estándar", "currency": "USD",
         "published_rate": 100.0, "closed": 0},
        {"date": "2026-08-01", "prop_id": 1, "hotel_label": "Hotel A",
         "rate_plan_id": "PLAN-1", "rate_plan_label": "Estándar",
         "room_type_id": "RT-2", "room_type_label": "Suite", "currency": "USD",
         "published_rate": 200.0, "closed": 1},
    ]
    s = _rate_summary(rows)
    assert s["avg_published_rate"] == 150.0
    assert s["closed_days"] == 1
    assert s["plans"] == 1
    assert s["by_rate_plan"]["PLAN-1"]["avg_published_rate"] == 150.0


def test_inventory_summary_averages_and_by_room_type():
    from src.app.modules.analytics.kpi_reports import _inventory_summary

    rows = [
        {"date": "2026-08-01", "prop_id": 1, "hotel_label": "Hotel A",
         "room_type_id": "RT-1", "room_type_label": "Estándar",
         "available_rooms": 8, "blocked_rooms": 2, "total_rooms": 10},
        {"date": "2026-08-01", "prop_id": 1, "hotel_label": "Hotel A",
         "room_type_id": "RT-2", "room_type_label": "Suite",
         "available_rooms": 4, "blocked_rooms": 0, "total_rooms": 4},
    ]
    s = _inventory_summary(rows)
    assert s["avg_available"] == 6.0
    assert s["avg_blocked"] == 1.0
    assert s["avg_total"] == 7.0
    assert s["by_room_type"]["RT-1"]["available_rooms"] == 8


def test_funnel_summary_conversion_and_breakdowns():
    from src.app.modules.analytics.kpi_reports import _funnel_summary

    rows = [
        {"date": "2012-11-01", "visitor_location_country_id": 1, "visitor_country_label": "Perú",
         "srch_destination_id": 10, "destination_label": "Cusco", "searches": 100,
         "clicks": 30, "reservations": 5, "revenue_usd": 500.0, "avg_booking_window": 2.5},
        {"date": "2012-11-01", "visitor_location_country_id": 2, "visitor_country_label": "Brasil",
         "srch_destination_id": 11, "destination_label": "Lima", "searches": 200,
         "clicks": 40, "reservations": 10, "revenue_usd": 1000.0, "avg_booking_window": 4.0},
    ]
    s = _funnel_summary(rows)
    assert s["searches"] == 300
    assert s["clicks"] == 70
    assert s["reservations"] == 15
    assert s["revenue_usd"] == 1500.0
    assert s["conversion_percent"] == 5.0
    assert s["by_country"][0]["visitor_country_label"] == "Brasil"
    assert s["by_destination"][0]["destination_label"] == "Lima"


def test_funnel_property_channel_summary_by_site():
    from src.app.modules.analytics.kpi_reports import _funnel_pc_summary

    rows = [
        {"date": "2012-11-12", "prop_id": 1, "hotel_label": "Hotel A", "site_id": 7,
         "site_label": "Expedia", "visitor_location_country_id": 1,
         "visitor_country_label": "Perú", "srch_destination_id": 10,
         "destination_label": "Cusco", "searches": 50, "clicks": 10,
         "reservations": 2, "revenue_usd": 200.0, "avg_booking_window": 1.5,
         "avg_length_of_stay": 3.0, "adults": 4, "children": 2, "rooms": 2},
    ]
    s = _funnel_pc_summary(rows)
    assert s["searches"] == 50
    assert s["reservations"] == 2
    assert s["avg_length_of_stay"] == 3.0
    assert s["adults"] == 4
    assert s["by_site"][0]["site_label"] == "Expedia"
    assert s["by_hotel"][0]["hotel_label"] == "Hotel A"


def test_validate_range_rejects_inverted():
    from src.app.modules.analytics.kpi_reports import _validate_range

    with pytest.raises(ValueError):
        _validate_range("2026-08-02", "2026-08-01", 30)


@pytest.mark.integration
def test_booking_dashboard_filters_by_date_range_real_clickhouse():
    """Integración: kpi_booking_daily responde con el rango completo."""
    from src.app.modules.analytics.kpi_reports import get_booking_dashboard

    try:
        result = get_booking_dashboard(date_from="2026-06-25", date_to="2026-08-21")
    except Exception as exc:  # pragma: no cover - ClickHouse opcional en tests
        pytest.skip(f"ClickHouse no disponible: {exc}")
    assert result["available"] is True
    assert result["date_from"] == "2026-06-25"
    assert result["summary"]["bookings"] == 17  # verificado contra Mongo
    assert result["summary"]["revenue_usd"] == 4417.9
    assert result["total"] >= 15


@pytest.mark.integration
def test_funnel_dashboard_counts_real_clickhouse():
    """Integración: kpi_funnel_daily se alimenta de tablas OPERATIVAS
    (click_events + booking_orders), nunca del dataset sintético GA03.

    La tabla ya no contiene las 800K búsquedas de la fact: debe reflejar los
    clics/reservas reales y no exponer ningún label del funnel 2012-2013.
    """
    from src.app.modules.analytics.kpi_reports import get_funnel_dashboard

    try:
        result = get_funnel_dashboard(date_from="2026-06-25", date_to="2026-08-21")
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"ClickHouse no disponible: {exc}")
    assert result["available"] is True
    assert result["summary"]["searches"] < 1000  # datos reales, no las 800K sintéticas
    assert result["total"] > 0
    # Ninguna fila puede venir del funnel sintético 2012-2013.
    assert not any(
        str(row.get("date") or "").startswith(("2012", "2013"))
        for row in result["rows"]
    )
