from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

PROJECT_ROOT = Path(os.getenv("HOTELDATA_PROJECT_ROOT", "/opt/hoteldata"))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.etl.tasks import (
    create_indexes,
    extract_csv,
    load_fact_events,
    load_rejected_records,
    save_execution_report,
    seed_master_collections_check,
    transform_fact_events,
    validate_environment,
    validate_master_keys,
    validate_schema,
)


with DAG(
    dag_id="hoteldata_taf01_etl_pipeline",
    description="HotelData Hub strict ETL pipeline for transactional fact events",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["hoteldata-hub", "taf01", "etl", "mongodb"],
) as dag:
    validate_environment_task = PythonOperator(
        task_id="validate_environment",
        python_callable=validate_environment,
    )
    seed_master_collections_check_task = PythonOperator(
        task_id="seed_master_collections_check",
        python_callable=seed_master_collections_check,
    )
    extract_csv_task = PythonOperator(
        task_id="extract_csv",
        python_callable=extract_csv,
    )
    validate_schema_task = PythonOperator(
        task_id="validate_schema",
        python_callable=validate_schema,
    )
    transform_fact_events_task = PythonOperator(
        task_id="transform_fact_events",
        python_callable=transform_fact_events,
    )
    validate_master_keys_task = PythonOperator(
        task_id="validate_master_keys",
        python_callable=validate_master_keys,
    )
    load_fact_events_task = PythonOperator(
        task_id="load_fact_events",
        python_callable=load_fact_events,
    )
    load_rejected_records_task = PythonOperator(
        task_id="load_rejected_records",
        python_callable=load_rejected_records,
    )
    create_indexes_task = PythonOperator(
        task_id="create_indexes",
        python_callable=create_indexes,
    )
    save_execution_report_task = PythonOperator(
        task_id="save_execution_report",
        python_callable=save_execution_report,
    )

    (
        validate_environment_task
        >> seed_master_collections_check_task
        >> extract_csv_task
        >> validate_schema_task
        >> transform_fact_events_task
        >> validate_master_keys_task
        >> load_fact_events_task
        >> load_rejected_records_task
        >> create_indexes_task
        >> save_execution_report_task
    )
