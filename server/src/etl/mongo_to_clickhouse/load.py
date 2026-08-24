"""Carga a ClickHouse: CREATE TABLE (ReplacingMergeTree) + rebuild por corrida.

Cada tabla KPI usa ``ReplacingMergeTree`` con ``ORDER BY`` = clave natural
completa. El refresh horario **recalcula el 100% de los agregados**, así que
``load_all`` hace ``TRUNCATE`` + INSERT por tabla: ClickHouse refleja siempre el
estado actual de Mongo. Sin el truncate, ``ReplacingMergeTree`` deja huérfanas
las claves que desaparecieron del origen (p.ej. una factura que pasó de
``issued`` a ``cancelled``, o una reserva que cambió de estado) porque la
corrida ya no emite la clave antigua y su fila obsoleta sigue visible.
"""

from __future__ import annotations

from typing import Any

from config.settings import get_settings
from src.etl.mongo_to_clickhouse.config import DEFAULT_REFRESH_MODE, INSERT_BATCH_SIZE, REFRESH_MODES
from src.etl.mongo_to_clickhouse.transform import TABLE_COLUMNS

# Esquemas DDL: (columnas tipadas, ORDER BY). Contrato con transform.TABLE_COLUMNS.
TABLES_DDL: dict[str, tuple[str, str]] = {
    "kpi_booking_daily": (
        "date Date, prop_id UInt32, hotel_label LowCardinality(String), room_type_id String, "
        "room_type_label LowCardinality(String), booking_source LowCardinality(String), "
        "status LowCardinality(String), bookings UInt32, nights UInt32, revenue_usd Decimal(18, 2), "
        "adults UInt32, children UInt32, cancelled UInt32",
        "(date, prop_id, room_type_id, booking_source, status)",
    ),
    "kpi_booking_nights_daily": (
        "date Date, prop_id UInt32, hotel_label LowCardinality(String), room_type_id String, "
        "room_type_label LowCardinality(String), currency LowCardinality(String), rooms_sold UInt32, room_nights UInt32, "
        "revenue Decimal(18, 2), cancelled_rooms UInt32, adults UInt32, children UInt32",
        "(date, prop_id, room_type_id, currency)",
    ),
    "kpi_inventory_daily": (
        "date Date, prop_id UInt32, hotel_label LowCardinality(String), room_type_id String, "
        "room_type_label LowCardinality(String), available_rooms UInt32, blocked_rooms UInt32, total_rooms UInt32",
        "(date, prop_id, room_type_id)",
    ),
    "kpi_rate_daily": (
        "date Date, prop_id UInt32, hotel_label LowCardinality(String), rate_plan_id String, "
        "rate_plan_label LowCardinality(String), room_type_id String, room_type_label LowCardinality(String), "
        "currency LowCardinality(String), published_rate Decimal(18, 2), closed UInt8",
        "(date, prop_id, rate_plan_id, room_type_id, currency)",
    ),
    "kpi_room_performance_daily": (
        "date Date, prop_id UInt32, hotel_label LowCardinality(String), room_type_id String, "
        "room_type_label LowCardinality(String), currency LowCardinality(String), booking_source LowCardinality(String), "
        "rooms_sold UInt32, room_nights UInt32, revenue Decimal(18, 2), cancelled_rooms UInt32, "
        "available_rooms UInt32, blocked_rooms UInt32, total_rooms UInt32, "
        "published_rate Nullable(Decimal(18, 2)), rate_variance Nullable(Decimal(18, 2))",
        "(date, prop_id, room_type_id, currency, booking_source)",
    ),
    "kpi_review_daily": (
        "date Date, prop_id UInt32, hotel_label LowCardinality(String), reviews UInt32, rating_sum Float64, avg_rating Float64, approved UInt32, pending UInt32, rejected UInt32, "
        "responded UInt32, positive UInt32, neutral UInt32, negative UInt32, moderated_count UInt32, "
        "avg_moderation_minutes Nullable(Float64), responded_count UInt32, avg_response_minutes Nullable(Float64)",
        "(date, prop_id)",
    ),
    "kpi_funnel_daily": (
        "date Date, visitor_location_country_id UInt32, visitor_country_label LowCardinality(String), "
        "srch_destination_id UInt32, destination_label LowCardinality(String), "
        "searches UInt64, clicks UInt64, reservations UInt64, revenue_usd Decimal(18, 2), "
        "avg_booking_window Float64",
        "(date, visitor_location_country_id, srch_destination_id)",
    ),
    "kpi_funnel_property_channel_daily": (
        "date Date, prop_id UInt32, hotel_label LowCardinality(String), site_id UInt32, "
        "site_label LowCardinality(String), visitor_location_country_id UInt32, "
        "visitor_country_label LowCardinality(String), srch_destination_id UInt32, "
        "destination_label LowCardinality(String), "
        "searches UInt64, clicks UInt64, reservations UInt64, "
        "revenue_usd Decimal(18, 2), avg_booking_window Float64, "
        "avg_length_of_stay Float64, adults UInt64, children UInt64, rooms UInt64",
        "(date, prop_id, site_id, visitor_location_country_id, srch_destination_id)",
    ),
    "kpi_housekeeping_daily": (
        "date Date, prop_id UInt32, hotel_label LowCardinality(String), tasks_total UInt64, "
        "tasks_completed UInt64, tasks_completed_on_time UInt64, tasks_with_completed_at UInt64, "
        "maintenance_total UInt64, maintenance_completed UInt64, maintenance_completed_on_time UInt64, "
        "rooms_status_events UInt64, rooms_to_clean UInt64, rooms_cleaned UInt64, "
        "rooms_available_after_cleaning UInt64, avg_cleaning_minutes Nullable(Float64), "
        "avg_checkout_to_available_minutes Nullable(Float64), rotation_observed UInt64, "
        "inventory_available_rooms UInt64, inventory_blocked_rooms UInt64, inventory_total_rooms UInt64, "
        "charges_total UInt64, charges_amount Decimal(18, 2), supplier_country_coverage UInt64",
        "(date, prop_id)",
    ),
    "kpi_invoice_daily": (
        "date Date, prop_id UInt32, hotel_label LowCardinality(String), status LowCardinality(String), "
        "invoice_count UInt32, subtotal Decimal(18, 2), taxes Decimal(18, 2), total Decimal(18, 2), "
        "paid_total Decimal(18, 2), pending_total Decimal(18, 2), cancelled_total Decimal(18, 2)",
        "(date, prop_id, status)",
    ),
    "kpi_payment_daily": (
        "date Date, prop_id UInt32, hotel_label LowCardinality(String), method LowCardinality(String), "
        "status LowCardinality(String), payment_count UInt32, paid_amount Decimal(18, 2), "
        "refunded_amount Decimal(18, 2), failed_amount Decimal(18, 2), invoiced_amount Decimal(18, 2), "
        "collected_amount Decimal(18, 2), outstanding_amount Decimal(18, 2)",
        "(date, prop_id, method, status)",
    ),
    # ── Capa estratégica mensual (TAF14): ``month`` = primer día del mes ─
    "strat_hotel_monthly": (
        "month Date, prop_id UInt32, hotel_label LowCardinality(String), currency LowCardinality(String), "
        "bookings UInt32, rooms_sold UInt32, room_nights UInt32, revenue Decimal(18, 2), "
        "discount_amount Decimal(18, 2), adults UInt32, children UInt32, cancelled_rooms UInt32, "
        "total_rooms UInt32, city LowCardinality(String), "
        "city_lat Nullable(Float64), city_lng Nullable(Float64)",
        "(month, prop_id, currency)",
    ),
    "strat_plan_monthly": (
        "month Date, prop_id UInt32, hotel_label LowCardinality(String), room_type_id String, "
        "room_type_label LowCardinality(String), currency LowCardinality(String), "
        "bookings UInt32, rooms_sold UInt32, room_nights UInt32, revenue Decimal(18, 2), "
        "discount_amount Decimal(18, 2), adults UInt32, children UInt32, cancelled_rooms UInt32",
        "(month, prop_id, room_type_id, currency)",
    ),
    "strat_market_monthly": (
        "month Date, visitor_location_country_id UInt32, visitor_country_label LowCardinality(String), "
        "srch_destination_id UInt32, destination_label LowCardinality(String), "
        "searches UInt64, clicks UInt64, reservations UInt64, revenue_usd Decimal(18, 2)",
        "(month, visitor_location_country_id, srch_destination_id)",
    ),
    "strat_reputation_monthly": (
        "month Date, prop_id UInt32, hotel_label LowCardinality(String), reviews UInt32, "
        "avg_rating Float64, positive UInt32, neutral UInt32, negative UInt32, responded UInt32, "
        "response_rate Float64",
        "(month, prop_id)",
    ),
}


# Tablas KPI sin TTL de retención. Los dos funnel se alimentan de tablas
# operativas (click_events + booking_orders) sin acumular historial entre
# corridas, así que la retención no aplica — y un TTL de meses purgaría su
# historial en cada merge, dejando los informes de funnel sin datos. Las
# tablas operacionales acumulativas sí quedan bajo retención.
TTL_EXEMPT_TABLES: frozenset[str] = frozenset(
    {
        "kpi_funnel_daily",
        "kpi_funnel_property_channel_daily",
        # La capa estratégica mensual necesita historial largo (comparaciones
        # trimestrales/semestrales/anuales); una retención mensual la purgaría.
        "strat_hotel_monthly",
        "strat_plan_monthly",
        "strat_market_monthly",
        "strat_reputation_monthly",
    }
)


# Columnas del contrato desnormalizado. Se aplican también a tablas KPI
# creadas por la versión anterior sin eliminar sus datos.
LABEL_COLUMNS: dict[str, tuple[tuple[str, str], ...]] = {
    "kpi_booking_daily": (("hotel_label", "LowCardinality(String)"), ("room_type_label", "LowCardinality(String)")),
    "kpi_booking_nights_daily": (("hotel_label", "LowCardinality(String)"), ("room_type_label", "LowCardinality(String)")),
    "kpi_inventory_daily": (("hotel_label", "LowCardinality(String)"), ("room_type_label", "LowCardinality(String)")),
    "kpi_rate_daily": (("hotel_label", "LowCardinality(String)"), ("rate_plan_label", "LowCardinality(String)"), ("room_type_label", "LowCardinality(String)")),
    "kpi_room_performance_daily": (("hotel_label", "LowCardinality(String)"), ("room_type_label", "LowCardinality(String)"), ("booking_source", "LowCardinality(String)")),
    "kpi_review_daily": (("hotel_label", "LowCardinality(String)"),),
    "kpi_funnel_daily": (("visitor_country_label", "LowCardinality(String)"), ("destination_label", "LowCardinality(String)")),
    "kpi_funnel_property_channel_daily": (("hotel_label", "LowCardinality(String)"), ("site_label", "LowCardinality(String)"), ("visitor_country_label", "LowCardinality(String)"), ("destination_label", "LowCardinality(String)")),
    "kpi_housekeeping_daily": (("hotel_label", "LowCardinality(String)"),),
    "kpi_invoice_daily": (("hotel_label", "LowCardinality(String)"),),
    "kpi_payment_daily": (("hotel_label", "LowCardinality(String)"),),
    "strat_hotel_monthly": (("hotel_label", "LowCardinality(String)"), ("city", "LowCardinality(String)")),
    "strat_plan_monthly": (("hotel_label", "LowCardinality(String)"), ("room_type_label", "LowCardinality(String)")),
    "strat_market_monthly": (("visitor_country_label", "LowCardinality(String)"), ("destination_label", "LowCardinality(String)")),
    "strat_reputation_monthly": (("hotel_label", "LowCardinality(String)"),),
}


# Columnas anulables añadidas por evolución de esquema (sin DEFAULT, igual que
# el DDL base). Se agregan idempotentemente a tablas ya existentes vía
# ``ALTER TABLE ... ADD COLUMN IF NOT EXISTS``, igual que ``LABEL_COLUMNS``
# pero sin el ``DEFAULT ''`` (válido solo para String). IE-H02 las usa para las
# coordenadas reales de ciudad (geo_catalog); ``None`` = sin dato, no fabricado.
NULLABLE_COLUMNS: dict[str, tuple[tuple[str, str], ...]] = {
    "strat_hotel_monthly": (
        ("city_lat", "Nullable(Float64)"),
        ("city_lng", "Nullable(Float64)"),
    ),
}


def clickhouse_client(settings=None):
    """Devuelve un cliente clickhouse-connect usando ``settings`` (o get_settings())."""
    import clickhouse_connect  # type: ignore

    settings = settings or get_settings()
    return clickhouse_connect.get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        username=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_database,
    )


def date_column_for(table_name: str) -> str:
    """Primera columna del ORDER BY: ``date`` en la capa táctica, ``month`` en la estratégica.

    Es la columna de partición/TTL y la que fechan los reportes de salud. Para
    tablas fuera del contrato (p.ej. fakes de tests) cae a ``date`` — el
    comportamiento histórico.
    """
    ddl = TABLES_DDL.get(table_name)
    if ddl is None:
        return "date"
    _, order_by = ddl
    return order_by.lstrip("(").split(",")[0].strip()


def _ddl_for(table_name: str, ttl_months: int = 0) -> str:
    columns_sql, order_by = TABLES_DDL[table_name]
    # La partición y el TTL se anclan a la primera columna del ORDER BY, que es
    # ``date`` en la capa táctica y ``month`` en la estratégica.
    date_column = date_column_for(table_name)
    partition_sql = ""
    if table_name in LABEL_COLUMNS:
        partition_sql = f" PARTITION BY toYYYYMM({date_column})"
    # Retención histórica: TTL sobre la columna de fecha (``date``/``month``).
    # Con 0 no se emite la cláusula, y las tablas de funnel + estratégicas
    # están exentas (necesitan historial largo). La purga ocurre en el merge,
    # así que el rebuild (TRUNCATE + INSERT del modo full) no se ve afectado.
    has_ttl = bool(ttl_months and ttl_months > 0) and table_name not in TTL_EXEMPT_TABLES
    ttl_sql = f" TTL {date_column} + INTERVAL {ttl_months} MONTH" if has_ttl else ""
    return (
        f"CREATE TABLE IF NOT EXISTS {table_name} "
        f"({columns_sql}, _etl_run_at DateTime DEFAULT now()) "
        f"ENGINE = ReplacingMergeTree(_etl_run_at){partition_sql} "
        f"ORDER BY {order_by}{ttl_sql}"
    )


# Claves de ordenamiento por tabla. ``kpi_room_performance_daily`` amplió su
# ORDER BY en R1.2 (canal) y requiere recrear la tabla; el pipeline reconstruye
# los agregados al 100% en cada corrida, así que DROP + CREATE es seguro.
_TABLE_ORDER_BY: dict[str, str] = {
    name: ddl_order for name, (ddl_columns, ddl_order) in TABLES_DDL.items()
}


def _table_create_sql(client, database: str, table_name: str) -> str | None:
    """Devuelve el CREATE TABLE actual de la tabla o None si no existe."""
    try:
        rows = client.query(
            f"SELECT create_table_query FROM system.tables "
            f"WHERE database = '{database}' AND name = '{table_name}'"
        ).result_rows
    except Exception:
        return None
    return rows[0][0] if rows else None


def create_tables(
    client,
    database: str,
    tables: tuple[str, ...],
    ttl_months: int = 0,
) -> dict[str, str]:
    """Crea/actualiza el esquema KPI sin copiar tablas de dimensiones.

    Las columnas de labels son una ampliación compatible: si una tabla ya
    existía desde una corrida anterior, ``ADD COLUMN IF NOT EXISTS`` la adapta
    sin borrar ni reescribir sus métricas históricas. Cuando el ORDER BY cambió
    (p.ej. ``kpi_room_performance_daily`` ganó ``booking_source`` en R1.2), el
    ADD COLUMN no basta porque ReplacingMergeTree deduplicaría por la clave
    vieja; en ese caso se recrea la tabla (DROP + CREATE) — seguro porque cada
    corrida recompone el 100% de los agregados.

    ``ttl_months`` (>0) agrega retención histórica por ``date`` de forma
    idempotente: el DDL nuevo lo incluye y las tablas existentes sin TTL se
    actualizan con ``ALTER TABLE ... MODIFY TTL`` (sin drop, sin tocar el
    historial). Con 0 no se emite ninguna cláusula/ALTER de TTL. Las tablas en
    ``TTL_EXEMPT_TABLES`` (funnel) quedan fuera de la retención para no purgar
    su snapshot histórico.
    """
    result: dict[str, str] = {}
    for table_name in tables:
        if table_name not in TABLES_DDL:
            result[table_name] = "skipped: sin esquema definido"
            continue
        client.command(f"CREATE DATABASE IF NOT EXISTS {database}")
        expected_order = _TABLE_ORDER_BY[table_name]
        existing_sql = _table_create_sql(client, database, table_name)
        if existing_sql and expected_order not in existing_sql:
            client.command(f"DROP TABLE IF EXISTS {database}.{table_name}")
        client.command(_ddl_for(table_name, ttl_months))
        for column_name, column_type in LABEL_COLUMNS.get(table_name, ()):
            client.command(
                f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS "
                f"{column_name} {column_type} DEFAULT ''"
            )
        for column_name, column_type in NULLABLE_COLUMNS.get(table_name, ()):
            client.command(
                f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS "
                f"{column_name} {column_type}"
            )
        if ttl_months and ttl_months > 0 and table_name not in TTL_EXEMPT_TABLES:
            client.command(
                f"ALTER TABLE {database}.{table_name} "
                f"MODIFY TTL date + INTERVAL {ttl_months} MONTH"
            )
        result[table_name] = "created"
    return result


def coerce_date_column(rows: list[list[Any]], table_name: str) -> list[list[Any]]:
    """Reconvierte la primera columna (``date``/``month``) a ``datetime.date``.

    El pipeline persiste el transformado como JSON entre stages
    (``write_json_file`` → ``read_json_file``) y ``_json_default`` convierte
    las fechas a strings ISO. clickhouse_connect exige la columna Date como
    ``datetime.date``; sin esta coerción el INSERT falla con
    ``TypeError: unsupported operand type(s) for -: 'str' and 'datetime.date'``.
    ``table_name`` documenta la intención (la primera columna es siempre la
    columna de fecha) y permite ampliar a más columnas si un esquema futuro
    tiene varias fechas.
    """
    from datetime import date as _date
    from datetime import datetime as _datetime

    if not rows:
        return rows

    def _coerce(value: Any) -> Any:
        if isinstance(value, _datetime):
            return value.date()
        if isinstance(value, _date):
            return value
        if isinstance(value, str) and value:
            try:
                return _date.fromisoformat(value.split("T")[0])
            except ValueError:
                return value  # no es una fecha: se conserva (fallará si es columna Date)
        return value

    return [[_coerce(row[0]) if i == 0 else v for i, v in enumerate(row)] for row in rows]


def load_table(client, database: str, table_name: str, columns: list[str], rows: list[list[Any]]) -> int:
    """Inserta filas transformadas en la tabla (batch). Devuelve el número de filas."""
    if not rows:
        return 0
    rows = coerce_date_column(rows, table_name)
    inserted = 0
    for start in range(0, len(rows), INSERT_BATCH_SIZE):
        batch = rows[start : start + INSERT_BATCH_SIZE]
        client.insert(
            table=table_name,
            data=batch,
            column_names=columns,
            database=database,
        )
        inserted += len(batch)
    return inserted


def load_all(
    client,
    database: str,
    payload: dict[str, list[list[Any]]],
    refresh_mode: str = DEFAULT_REFRESH_MODE,
) -> dict[str, int]:
    """Carga todas las tablas del payload ``{tabla: filas}`` y reporta conteos.

    ``refresh_mode`` (configurable en la UI, leído por el DAG en cada corrida):

    - ``"full"`` (default): rebuild por tabla — ``TRUNCATE`` antes del INSERT
      porque los KPI son agregados 100% recalculados. Elimina filas huérfanas
      de claves que ya no existen en el origen (cambios de estado, anulaciones,
      bajas) que un upsert puro de ``ReplacingMergeTree`` jamás reemplaza.
    - ``"incremental"``: sin borrado — INSERT y ``OPTIMIZE TABLE ... FINAL``
      para colapsar de inmediato las versiones de cada clave natural (la más
      nueva gana vía ``_etl_run_at``). Conserva el historial intacto y nunca
      deja una tabla vacía ante un fallo a mitad de corrida; las claves
      eliminadas en Mongo pueden permanecer hasta una corrida ``full``.

    Un modo desconocido lanza ``ValueError`` en vez de truncar en silencio.
    """
    if refresh_mode not in REFRESH_MODES:
        raise ValueError(
            f"refresh_mode desconocido: {refresh_mode!r} (válidos: {', '.join(REFRESH_MODES)})"
        )
    counts: dict[str, int] = {}
    for table_name, rows in payload.items():
        columns = TABLE_COLUMNS.get(table_name)
        if columns is None:
            counts[table_name] = -1
            continue
        if refresh_mode == "full":
            client.command(f"TRUNCATE TABLE {database}.{table_name}")
        counts[table_name] = load_table(client, database, table_name, columns, rows)
        if refresh_mode == "incremental":
            client.command(f"OPTIMIZE TABLE {database}.{table_name} FINAL")
    return counts
