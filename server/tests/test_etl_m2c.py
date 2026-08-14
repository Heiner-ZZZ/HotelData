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


def test_transform_drops_rows_without_valid_date():
    """Filas sin fecha válida nunca llegan a ClickHouse (nada de 1970-01-01)."""
    from src.etl.mongo_to_clickhouse.transform import transform_rows

    docs = [
        {"date": "2026-08-02", "prop_id": 1, "bookings": 2},   # válida
        {"date": "", "prop_id": 2, "bookings": 1},             # vacía → descartar
        {"date": "fecha-ilegible", "prop_id": 3, "bookings": 1},  # basura → descartar
        {"date": "2026-13-45", "prop_id": 4, "bookings": 1},  # mes/día inválido → descartar
        {},                                                       # sin campo date → descartar
    ]
    rows = transform_rows("kpi_booking_daily", docs)
    assert len(rows) == 1
    assert rows[0][0].strftime("%Y-%m-%d") == "2026-08-02"
    assert rows[0][1] == 1
    assert all(row[0] != "1970-01-01" for row in rows)


def test_transform_with_stats_counts_discarded_by_invalid_date():
    """``transform_rows_with_stats`` devuelve filas válidas y el conteo de descartadas."""
    from src.etl.mongo_to_clickhouse.transform import transform_rows_with_stats

    docs = [
        {"date": "2026-08-02", "prop_id": 1, "bookings": 2},
        {"date": "2026-08-02", "prop_id": 2, "bookings": 3},
        {"date": "", "prop_id": 3, "bookings": 1},
        {"date": "no-es-fecha", "prop_id": 4, "bookings": 1},
    ]
    rows, discarded = transform_rows_with_stats("kpi_booking_daily", docs)
    assert len(rows) == 2
    assert discarded == 2


def test_quality_report_includes_discarded_rows():
    """El reporte de calidad cuenta las filas descartadas por fecha inválida."""
    from src.etl.mongo_to_clickhouse.reports import run_quality_checks

    quality = run_quality_checks(
        {"kpi_booking_daily": 2, "kpi_inventory_daily": 5},
        discarded_by_table={"kpi_booking_daily": 2, "kpi_inventory_daily": 0},
    )
    assert quality["tables"]["kpi_booking_daily"]["discarded_rows"] == 2
    assert quality["tables"]["kpi_inventory_daily"]["discarded_rows"] == 0
    assert quality["discarded_rows"] == 2
    assert quality["discarded_reason"] == "invalid_date"


class _FakeHealthClient:
    """Cliente mínimo que devuelve la salud de fechas por tabla (simula CH)."""

    def __init__(self, results: dict[str, list]) -> None:
        self.results = results

    def query(self, sql: str):
        class _Rows:
            def __init__(self, rows: list) -> None:
                self.result_rows = rows

        table = sql.rsplit(".", 1)[-1].strip()
        return _Rows([self.results[table]])


def test_date_health_check_warns_on_epoch_rows_and_empty_range():
    """1970-01-01 o rango vacío marcan warning en la tabla (datos mal fechados)."""
    from datetime import date

    from src.etl.mongo_to_clickhouse.reports import run_date_health_checks

    client = _FakeHealthClient({
        "kpi_a": [10, 0, date(2026, 6, 26), date(2026, 8, 20)],
        "kpi_b": [5, 2, date(1970, 1, 1), date(2026, 8, 20)],
        "kpi_c": [3, 3, date(1970, 1, 1), date(1970, 1, 1)],
        "kpi_d": [0, 0, None, None],
    })
    checks = run_date_health_checks(
        client, "hoteldata", ("kpi_a", "kpi_b", "kpi_c", "kpi_d")
    )
    assert checks["tables"]["kpi_a"]["state"] == "ok"
    assert checks["tables"]["kpi_a"]["epoch_rows"] == 0
    assert checks["tables"]["kpi_b"]["state"] == "warn"
    assert checks["tables"]["kpi_b"]["epoch_rows"] == 2
    assert checks["tables"]["kpi_c"]["state"] == "warn"
    assert checks["tables"]["kpi_c"]["empty_range"] is True
    assert checks["tables"]["kpi_d"]["state"] == "no_rows"
    assert checks["warned_tables"] == ["kpi_b", "kpi_c"]
    assert checks["ok"] is False


@pytest.mark.integration
def test_reputation_analytics_filters_by_explicit_date_range():
    """El endpoint de reputación acepta date_from/date_to y filtra por ambos límites."""
    from src.app.modules.reviews.service.lifecycle.reports import get_reputation_analytics

    try:
        result = get_reputation_analytics(date_from="2026-07-24", date_to="2026-07-24")
    except TypeError:
        raise  # RED: el parámetro date_from/date_to aún no existe
    except Exception as exc:  # pragma: no cover - ClickHouse opcional en tests
        pytest.skip(f"ClickHouse no disponible: {exc}")
    assert result["available"] is True
    assert result["date_from"] == "2026-07-24"
    assert result["date_to"] == "2026-07-24"
    assert any(row["date"] == "2026-07-24" for row in result["rows"])

    # Rango que no contiene el único día con reviews → sin filas.
    empty = get_reputation_analytics(date_from="2026-07-01", date_to="2026-07-02")
    assert empty["rows"] == []


def test_reputation_analytics_rejects_inverted_date_range():
    """date_to anterior a date_from es un error de contrato (400 en la ruta)."""
    from src.app.modules.reviews.service.lifecycle.reports import get_reputation_analytics

    with pytest.raises(ValueError):
        get_reputation_analytics(date_from="2026-07-02", date_to="2026-07-01")


def test_date_health_check_ok_when_all_dates_healthy():
    """Sin filas épsilon ni rangos vacíos, el check pasa limpio."""
    from datetime import date

    from src.etl.mongo_to_clickhouse.reports import run_date_health_checks

    client = _FakeHealthClient({
        "kpi_a": [10, 0, date(2026, 6, 26), date(2026, 8, 20)],
        "kpi_d": [0, 0, None, None],
    })
    checks = run_date_health_checks(client, "hoteldata", ("kpi_a", "kpi_d"))
    assert checks["ok"] is True
    assert checks["warned_tables"] == []
    assert checks["tables"]["kpi_a"]["min_date"] == "2026-06-26"
    assert checks["tables"]["kpi_a"]["max_date"] == "2026-08-20"


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


def test_load_all_incremental_skips_truncate_and_optimizes():
    """Modo incremental: sin TRUNCATE, INSERT + ``OPTIMIZE ... FINAL``.

    El incremental no sobrescribe todo: conserva el historial intacto y deja
    que ``ReplacingMergeTree`` colapse por clave natural (la versión más nueva
    gana vía ``_etl_run_at``). El ``OPTIMIZE FINAL`` colapsa las partes de
    inmediato para que las consultas no vean versiones duplicadas antes del
    merge en background.
    """
    from src.etl.mongo_to_clickhouse.load import load_all

    client = _FakeClickHouseClient()
    payload = {
        "kpi_invoice_daily": [
            ["2026-08-01", 1, "Hotel A", "cancelled", 1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        ],
    }
    counts = load_all(client, "hoteldata", payload, refresh_mode="incremental")
    assert counts == {"kpi_invoice_daily": 1}
    assert client.commands == ["OPTIMIZE TABLE hoteldata.kpi_invoice_daily FINAL"]
    assert client.inserts == [("kpi_invoice_daily", 1)]


def test_load_all_rejects_unknown_refresh_mode():
    """Un modo desconocido no debe truncar silenciosamente (riesgo de borrado)."""
    from src.etl.mongo_to_clickhouse.load import load_all

    client = _FakeClickHouseClient()
    with pytest.raises(ValueError):
        load_all(client, "hoteldata", {"kpi_invoice_daily": []}, refresh_mode="bogus")


class _FakeCreateTablesClient:
    """Cliente mínimo para verificar CREATE/ALTER de create_tables (TTL)."""

    def __init__(self, existing: dict[str, str] | None = None) -> None:
        self.existing = existing or {}
        self.commands: list[str] = []

    def query(self, sql: str):
        for table, create_sql in self.existing.items():
            if table in sql:
                return type("R", (), {"result_rows": [[create_sql]]})()
        return type("R", (), {"result_rows": []})()

    def command(self, sql: str) -> None:
        self.commands.append(sql)


def test_ddl_includes_monthly_partition_and_ttl():
    """Toda tabla KPI particiona por mes; el TTL aplica salvo funnel exento."""
    from src.etl.mongo_to_clickhouse.load import TTL_EXEMPT_TABLES, TABLES_DDL, _ddl_for

    for table in TABLES_DDL:
        ddl = _ddl_for(table, ttl_months=24)
        assert "PARTITION BY toYYYYMM(date)" in ddl, table
        if table in TTL_EXEMPT_TABLES:
            assert "TTL" not in ddl, table
        else:
            assert "TTL date + INTERVAL 24 MONTH" in ddl, table
            assert ddl.rstrip().endswith("MONTH"), table


def test_funnel_tables_are_exempt_from_ttl():
    """Los funnel (snapshot estático legacy) no se purgan por retención.

    Un TTL de meses borraría todo su historial 2012-2013 en el primer merge,
    dejando los informes de funnel sin datos; la retención solo aplica a las
    tablas operacionales que acumulan.
    """
    from src.etl.mongo_to_clickhouse.load import TTL_EXEMPT_TABLES, create_tables

    assert "kpi_funnel_daily" in TTL_EXEMPT_TABLES
    assert "kpi_funnel_property_channel_daily" in TTL_EXEMPT_TABLES
    client = _FakeCreateTablesClient()
    create_tables(client, "hoteldata", ("kpi_funnel_daily",), ttl_months=24)
    assert not any("MODIFY TTL" in c for c in client.commands)
    create_cmds = [c for c in client.commands if c.startswith("CREATE TABLE")]
    assert create_cmds and "TTL" not in create_cmds[0]


def test_create_tables_applies_ttl_to_existing_table():
    """Tablas ya creadas (sin TTL) se actualizan sin drop: ALTER MODIFY TTL.

    El rebuild no se ve afectado: el ORDER BY no cambió, así que la tabla NO
    se recrea (no se pierde historial) y el TTL se agrega de forma idempotente.
    """
    from src.etl.mongo_to_clickhouse.load import create_tables

    existing = {
        "kpi_invoice_daily": (
            "CREATE TABLE hoteldata.kpi_invoice_daily "
            "(date Date, ...) ENGINE = ReplacingMergeTree(_etl_run_at) "
            "PARTITION BY toYYYYMM(date) ORDER BY (date, prop_id, status)"
        )
    }
    client = _FakeCreateTablesClient(existing)
    create_tables(client, "hoteldata", ("kpi_invoice_daily",), ttl_months=24)
    assert not any("DROP TABLE" in c for c in client.commands)
    ttl_commands = [c for c in client.commands if "MODIFY TTL" in c]
    assert ttl_commands == [
        "ALTER TABLE hoteldata.kpi_invoice_daily MODIFY TTL date + INTERVAL 24 MONTH"
    ]


def test_create_tables_skips_ttl_when_disabled():
    """ttl_months=0: sin cláusula TTL en el DDL ni ALTER MODIFY TTL."""
    from src.etl.mongo_to_clickhouse.load import create_tables

    client = _FakeCreateTablesClient()
    create_tables(client, "hoteldata", ("kpi_invoice_daily",), ttl_months=0)
    assert not any("MODIFY TTL" in c for c in client.commands)
    create_cmds = [c for c in client.commands if c.startswith("CREATE TABLE")]
    assert create_cmds and "TTL" not in create_cmds[0]


def test_kpi_ttl_months_default_from_settings():
    """La retención se configura por entorno (default > 0)."""
    from config.settings import get_settings

    assert get_settings().kpi_ttl_months > 0


def test_resolve_refresh_mode_falls_back_to_full():
    """Sin configuración previa, el modo por defecto es 'full' (barrido)."""
    from src.etl.mongo_to_clickhouse.pipeline import resolve_refresh_mode

    assert resolve_refresh_mode() == "full"


def test_schedule_refresh_mode_round_trip():
    """El refresh_mode persiste en ``etl_pipeline_config`` junto al horario."""
    from src.app.features.etl_status_m2c.services.schedule_service import (
        get_schedule,
        update_schedule,
    )

    update_schedule("5 * * * *", True, refresh_mode="incremental")
    try:
        doc = get_schedule()
        assert doc["schedule_cron"] == "5 * * * *"
        assert doc["refresh_mode"] == "incremental"
    finally:
        update_schedule("5 * * * *", True, refresh_mode="full")
        restored = get_schedule()
        assert restored["refresh_mode"] == "full"
