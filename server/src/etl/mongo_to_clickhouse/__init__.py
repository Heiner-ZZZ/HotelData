"""Pipeline ETL MongoDB → ClickHouse (capa táctica de KPIs).

Paquete independiente de ``ga03_airflow`` — ver docs/PLAN_ETL_MONGO_TO_CLICKHOUSE.md.
"""

from src.etl.mongo_to_clickhouse.pipeline import (
    run_pipeline,
    validate_config,
    stage_validate_config,
    stage_extract_mongo,
    stage_transform,
    stage_create_tables,
    stage_load_clickhouse,
    stage_quality_report,
    stage_execution_report,
)
from src.etl.mongo_to_clickhouse.reports import run_quality_checks, save_execution_report
from src.etl.mongo_to_clickhouse.load import create_tables, load_all, load_table
from src.etl.mongo_to_clickhouse.transform import transform_rows
from src.etl.mongo_to_clickhouse.extract import (
    extract_all,
    extract_kpi_booking_daily,
    extract_kpi_booking_nights_daily,
    extract_kpi_inventory_daily,
    extract_kpi_rate_daily,
    extract_kpi_room_performance_daily,
    extract_kpi_review_daily,
    extract_kpi_funnel_daily,
    extract_kpi_funnel_property_channel_daily,
    extract_kpi_housekeeping_daily,
    extract_kpi_invoice_daily,
    extract_kpi_payment_daily,
)

__all__ = [
    "validate_config",
    "run_pipeline",
    "stage_validate_config",
    "stage_extract_mongo",
    "stage_transform",
    "stage_create_tables",
    "stage_load_clickhouse",
    "stage_quality_report",
    "stage_execution_report",
    "extract_all",
    "extract_kpi_booking_daily",
    "extract_kpi_booking_nights_daily",
    "extract_kpi_inventory_daily",
    "extract_kpi_rate_daily",
    "extract_kpi_room_performance_daily",
    "extract_kpi_review_daily",
    "extract_kpi_funnel_daily",
    "extract_kpi_funnel_property_channel_daily",
    "extract_kpi_housekeeping_daily",
    "extract_kpi_invoice_daily",
    "extract_kpi_payment_daily",
    "transform_rows",
    "create_tables",
    "load_table",
    "load_all",
    "run_quality_checks",
    "save_execution_report",
]
