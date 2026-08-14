"""DAG horario: MongoDB (operacional) → ClickHouse (táctico, KPIs).

Carga las tablas KPI de la primera entrega: rendimiento Revenue nocturno (`kpi_booking_nights_daily`,
`kpi_inventory_daily`, `kpi_rate_daily`, `kpi_room_performance_daily`, `kpi_review_daily`), compatibilidad de reservas; reviews permanece en Mongo y solo viaja el agregado táctico,
además de los dos resúmenes de funnel, siempre con agregaciones en origen. El horario se lee de la colección
``etl_pipeline_config`` en MongoDB (configurable desde la UI de monitoreo);
si la colección no existe, usa el fallback ``0 * * * *`` (cada hora en punto).

Independiente del DAG GA03 — no comparte imports (ver docs/PLAN_ETL_MONGO_TO_CLICKHOUSE.md).
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

PROJECT_ROOT = Path(os.getenv("HOTELDATA_PROJECT_ROOT", "/opt/hoteldata"))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import get_settings
from src.etl.mongo_to_clickhouse.pipeline import (
    stage_create_tables,
    stage_execution_report,
    stage_extract_mongo,
    stage_load_clickhouse,
    stage_quality_report,
    stage_transform,
    stage_validate_config,
)
from src.etl.mongo_to_clickhouse.config import (
    DEFAULT_SCHEDULE_CRON,
    ETL_PIPELINE_CONFIG_COLLECTION,
)


def _resolve_schedule() -> str | None:
    """Lee el horario configurado; ``None`` pausa el DAG cuando la UI lo deshabilita."""
    try:
        settings = get_settings()
        from pymongo import MongoClient

        client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=3000)
        try:
            doc = client[settings.mongo_database][ETL_PIPELINE_CONFIG_COLLECTION].find_one(
                {"pipeline": "mongo_to_clickhouse"}
            )
            if doc:
                if not doc.get("enabled", True):
                    return None
                if doc.get("schedule_cron"):
                    return str(doc["schedule_cron"])
        finally:
            client.close()
    except Exception:  # pragma: no cover - fallback silencioso
        pass
    return DEFAULT_SCHEDULE_CRON


with DAG(
    dag_id="hoteldata_mongo_to_clickhouse_etl",
    description=(
        "ETL horario MongoDB (operacional) → ClickHouse (táctico): KPI agregados "
        "para los informes compuestos de TA12"
    ),
    start_date=datetime(2026, 1, 1),
    schedule=_resolve_schedule(),
    catchup=False,
    tags=["hoteldata-hub", "m2c", "clickhouse", "kpi", "etl"],
) as dag:
    validate_config_task = PythonOperator(
        task_id="validate_config",
        python_callable=stage_validate_config,
        op_kwargs={"run_date": "{{ ds }}"},
    )
    # ``run_date`` ({{ ds }}) fecha la subcarpeta diaria del directorio Dato:
    # <Dato>/<Seccion>/<YYYY-MM-DD>/<tabla>.parquet.
    extract_mongo_task = PythonOperator(
        task_id="extract_mongo",
        python_callable=stage_extract_mongo,
        op_kwargs={"run_date": "{{ ds }}"},
    )
    transform_task = PythonOperator(
        task_id="transform",
        python_callable=stage_transform,
        op_kwargs={"run_date": "{{ ds }}"},
    )
    create_tables_task = PythonOperator(
        task_id="create_tables",
        python_callable=stage_create_tables,
    )
    # Retry del load: cada tabla se TRUNCA antes del INSERT (rebuild del
    # agregado), así que un fallo entre ambos deja la tabla vacía hasta la
    # siguiente corrida. El reintento re-ejecuta load_all completo (idempotente)
    # y la autocurura sin intervención.
    load_clickhouse_task = PythonOperator(
        task_id="load_clickhouse",
        python_callable=stage_load_clickhouse,
        op_kwargs={"run_date": "{{ ds }}"},
        retries=1,
        retry_delay=timedelta(seconds=30),
    )
    quality_report_task = PythonOperator(
        task_id="quality_report",
        python_callable=stage_quality_report,
    )
    execution_report_task = PythonOperator(
        task_id="execution_report",
        python_callable=stage_execution_report,
    )

    (
        validate_config_task
        >> extract_mongo_task
        >> transform_task
        >> create_tables_task
        >> load_clickhouse_task
        >> quality_report_task
        >> execution_report_task
    )
