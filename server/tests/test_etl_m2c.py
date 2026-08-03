"""Tests del pipeline MongoDB → ClickHouse (capa táctica de KPIs).

Cubren las piezas que no requieren ClickHouse levantado: mappers de
``transform``, configuración de tablas y la agregación de ``booking_orders``
(integración con MongoDB real si está disponible, sin fallar si no).
"""

from __future__ import annotations

import pytest

from src.etl.mongo_to_clickhouse.config import ALL_TABLES, FACT_TABLES
from src.etl.mongo_to_clickhouse.transform import TABLE_COLUMNS, transform_rows


def test_all_tables_have_schemas():
    """Cada tabla del pipeline tiene columnas en transform y DDL en load."""
    from src.etl.mongo_to_clickhouse.load import TABLES_DDL

    assert set(ALL_TABLES) == set(FACT_TABLES)
    for table in ALL_TABLES:
        assert table in TABLE_COLUMNS, f"transform sin columnas para {table}"
        assert table in TABLES_DDL, f"load sin DDL para {table}"


def test_kpi_booking_mapper_positions():
    doc = {
        "date": "2026-06-26",
        "prop_id": 1,
        "room_type_id": "RT-1-standard",
        "booking_source": "cliente",
        "status": "confirmed",
        "bookings": 2,
        "nights": 3,
        "revenue_usd": 99.5,
        "adults": 2,
        "children": 1,
        "cancelled": 0,
    }
    rows = transform_rows("kpi_booking_daily", [doc])
    assert rows[0][0].strftime("%Y-%m-%d") == "2026-06-26"
    assert rows[0][1] == 1
    assert rows[0][2] == ""
    assert rows[0][3] == "RT-1-standard"
    assert rows[0][7] == 2
    assert rows[0][8] == 3
    assert rows[0][9] == 99.5


def test_revenue_kpi_mappers_and_currency_are_preserved():
    rows = transform_rows("kpi_booking_nights_daily", [{
        "date": "2026-08-02", "prop_id": 1, "room_type_id": "RT-1",
        "currency": "PEN", "rooms_sold": 2, "room_nights": 2,
        "revenue": 300, "cancelled_rooms": 0, "adults": 2, "children": 0,
    }])
    assert rows[0][0].strftime("%Y-%m-%d") == "2026-08-02"
    assert rows[0][5] == "PEN"
    assert rows[0][6:9] == [2, 2, 300.0]

    inventory = transform_rows("kpi_inventory_daily", [{
        "date": "2026-08-02", "prop_id": 1, "room_type_id": "RT-1",
        "available_rooms": 4, "blocked_rooms": 1, "total_rooms": 5,
    }])
    assert inventory[0][5:] == [4, 1, 5]


def test_room_performance_mapper_allows_unoccupied_inventory_rows():
    rows = transform_rows("kpi_room_performance_daily", [{
        "date": "2026-08-02", "prop_id": 1, "room_type_id": "RT-1", "currency": "",
        "rooms_sold": 0, "room_nights": 0, "revenue": 0, "cancelled_rooms": 0,
        "available_rooms": 4, "blocked_rooms": 1, "total_rooms": 5,
        "published_rate": None, "rate_variance": None,
    }])
    assert rows[0][6:13] == [0, 0, 0.0, 0, 4, 1, 5]
    assert rows[0][-2:] == [None, None]


def test_reviews_remain_operational_and_only_daily_kpi_is_tactical():
    assert "fact_reviews" not in ALL_TABLES
    assert "fact_reviews" not in TABLE_COLUMNS


def test_kpi_review_mapper_preserves_reputation_metrics_and_null_times():
    rows = transform_rows("kpi_review_daily", [{
        "date": "2026-08-02", "prop_id": 1, "reviews": 3, "rating_sum": 13,
        "avg_rating": 4.333, "approved": 2, "pending": 1, "rejected": 0,
        "responded": 1, "positive": 2, "neutral": 1, "negative": 0,
        "moderated_count": 2, "avg_moderation_minutes": 18.5,
        "responded_count": 1, "avg_response_minutes": None,
    }])
    assert rows[0][0].strftime("%Y-%m-%d") == "2026-08-02"
    assert rows[0][1:10] == [1, "", 3, 13.0, 4.333, 2, 1, 0, 1]
    assert rows[0][10:14] == [2, 1, 0, 2]
    assert rows[0][14] == 18.5
    assert rows[0][16] is None


def test_kpi_funnel_mapper_positions():
    doc = {
        "date": "2013-04-04",
        "visitor_location_country_id": 187,
        "srch_destination_id": 8250,
        "searches": 10,
        "clicks": 3,
        "reservations": 1,
        "revenue_usd": 104.77,
        "avg_booking_window": 12.5,
    }
    rows = transform_rows("kpi_funnel_daily", [doc])
    assert rows[0][1] == 187
    assert rows[0][2] == ""
    assert rows[0][3] == 8250
    assert rows[0][4] == ""
    assert rows[0][5] == 10
    assert rows[0][8] == 104.77


def test_kpi_funnel_property_channel_mapper_preserves_tactical_dimensions():
    doc = {
        "date": "2026-08-02",
        "prop_id": 42,
        "hotel_label": "Hotel 42",
        "site_id": 7,
        "site_label": "Canal 7",
        "visitor_location_country_id": 187,
        "visitor_country_label": "País 187",
        "srch_destination_id": 8250,
        "destination_label": "Destino 8250",
        "searches": 100,
        "clicks": 12,
        "reservations": 4,
        "revenue_usd": 512.75,
        "avg_booking_window": 9.5,
        "avg_length_of_stay": 2.25,
        "adults": 6,
        "children": 1,
        "rooms": 4,
    }
    rows = transform_rows("kpi_funnel_property_channel_daily", [doc])
    assert rows[0][1:9] == [42, "Hotel 42", 7, "Canal 7", 187, "País 187", 8250, "Destino 8250"]
    assert rows[0][9:12] == [100, 12, 4]
    assert rows[0][12] == 512.75
    assert rows[0][14:] == [2.25, 6, 1, 4]


def test_kpi_invoice_mapper_positions():
    doc = {
        "date": "2026-08-02", "prop_id": 1, "hotel_label": "Hotel Uno",
        "status": "paid", "invoice_count": 3, "subtotal": 900.0, "taxes": 90.0,
        "total": 990.0, "paid_total": 990.0, "pending_total": 0.0,
        "cancelled_total": 0.0,
    }
    rows = transform_rows("kpi_invoice_daily", [doc])
    assert rows[0][0].strftime("%Y-%m-%d") == "2026-08-02"
    assert rows[0][1:5] == [1, "Hotel Uno", "paid", 3]
    assert rows[0][5:] == [900.0, 90.0, 990.0, 990.0, 0.0, 0.0]


def test_kpi_payment_mapper_positions():
    doc = {
        "date": "2026-08-02", "prop_id": 1, "hotel_label": "Hotel Uno",
        "method": "card", "status": "confirmed", "payment_count": 2,
        "paid_amount": 100.0, "refunded_amount": 0.0, "failed_amount": 0.0,
        "invoiced_amount": 150.0, "collected_amount": 100.0, "outstanding_amount": 50.0,
    }
    rows = transform_rows("kpi_payment_daily", [doc])
    assert rows[0][0].strftime("%Y-%m-%d") == "2026-08-02"
    assert rows[0][1:5] == [1, "Hotel Uno", "card", "confirmed"]
    assert rows[0][5:] == [2, 100.0, 0.0, 0.0, 150.0, 100.0, 50.0]


def test_mappers_handle_missing_fields():
    """Campos ausentes no rompen los mappers (defaults defensivos)."""
    rows = transform_rows("kpi_booking_daily", [{"date": "2026-08-02", "prop_id": 1}])
    assert rows[0][0].strftime("%Y-%m-%d") == "2026-08-02"
    assert rows[0][1] == 1
    assert rows[0][2] == ""


@pytest.mark.integration
def test_extract_kpi_booking_aggregates_real_data():
    """Integración ligera: la agregación de booking_orders funciona con Mongo real.

    Se salta si Mongo no está disponible (no falla el resto de la suite).
    """
    try:
        from src.etl.mongo_to_clickhouse.extract import extract_kpi_booking_daily
    except ImportError:  # pragma: no cover
        pytest.skip("módulo extract no disponible")
    try:
        rows = extract_kpi_booking_daily(client=None, db_name="hoteldata_hub")
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"MongoDB no disponible: {exc}")
    assert isinstance(rows, list)
    for row in rows:
        assert "date" in row
        assert "prop_id" in row
        assert row["bookings"] >= 1


class _FakeClickHouseClient:
    """Cliente mínimo para verificar el orden TRUNCATE → INSERT de load_all."""

    def __init__(self) -> None:
        self.commands: list[str] = []
        self.inserts: list[tuple[str, int]] = []

    def command(self, sql: str) -> None:
        self.commands.append(sql)

    def insert(self, *, table: str, data: list, column_names: list, database: str) -> None:
        self.inserts.append((table, len(data)))


def test_load_all_rebuilds_tables_with_truncate_before_insert():
    """Cada tabla se TRUNCA antes del INSERT (rebuild del agregado).

    Esto evita que ``ReplacingMergeTree`` deje filas huérfanas de claves que
    desaparecieron del origen (p.ej. factura ``issued`` → ``cancelled``): sin
    el truncate, la corrida no emite la clave antigua y su fila sigue visible.
    """
    from src.etl.mongo_to_clickhouse.load import load_all

    client = _FakeClickHouseClient()
    payload = {
        "kpi_invoice_daily": [
            ["2026-08-01", 1, "Hotel A", "cancelled", 1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        ],
        "kpi_payment_daily": [
            ["2026-08-01", 1, "Hotel A", "card", "confirmed", 1, 10.0, 0.0, 0.0, 10.0, 10.0, 0.0],
        ],
    }
    counts = load_all(client, "hoteldata", payload)
    assert counts == {"kpi_invoice_daily": 1, "kpi_payment_daily": 1}
    assert client.commands == [
        "TRUNCATE TABLE hoteldata.kpi_invoice_daily",
        "TRUNCATE TABLE hoteldata.kpi_payment_daily",
    ]
    assert client.inserts == [("kpi_invoice_daily", 1), ("kpi_payment_daily", 1)]
