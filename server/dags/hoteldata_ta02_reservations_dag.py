from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

PROJECT_ROOT = Path(os.getenv("HOTELDATA_PROJECT_ROOT", "/opt/hoteldata"))
SERVER_ROOT = PROJECT_ROOT / "server"
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from src.etl.ta02_airflow_tasks import (
    convert_to_parquet,
    create_indexes,
    extract_from_pocketbase,
    load_dimensions_to_mongodb,
    load_fact_to_mongodb,
    run_quality_checks,
    save_pocketbase_extract,
    save_execution_report,
    transform_dimensions,
    transform_fact_reservations,
    validate_environment,
    validate_parquet_schema,
)


with DAG(
    dag_id="hoteldata_ta02_reservations_pipeline",
    description="HotelData TA 02 ETL: PocketBase to Parquet to MongoDB dimensional reservations model",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["hoteldata-hub", "ta02", "reservations", "mongodb", "parquet"],
) as dag:
    validate_environment_task = PythonOperator(
        task_id="validate_environment",
        python_callable=validate_environment,
    )
    extract_from_pocketbase_task = PythonOperator(
        task_id="extract_from_pocketbase",
        python_callable=extract_from_pocketbase,
    )
    save_pocketbase_extract_task = PythonOperator(
        task_id="save_pocketbase_extract",
        python_callable=save_pocketbase_extract,
    )
    convert_to_parquet_task = PythonOperator(
        task_id="convert_to_parquet",
        python_callable=convert_to_parquet,
    )
    validate_parquet_schema_task = PythonOperator(
        task_id="validate_parquet_schema",
        python_callable=validate_parquet_schema,
    )
    transform_dimensions_task = PythonOperator(
        task_id="transform_dimensions",
        python_callable=transform_dimensions,
    )
    transform_fact_reservations_task = PythonOperator(
        task_id="transform_fact_reservations",
        python_callable=transform_fact_reservations,
    )
    load_dimensions_to_mongodb_task = PythonOperator(
        task_id="load_dimensions_to_mongodb",
        python_callable=load_dimensions_to_mongodb,
    )
    load_fact_to_mongodb_task = PythonOperator(
        task_id="load_fact_to_mongodb",
        python_callable=load_fact_to_mongodb,
    )
    create_indexes_task = PythonOperator(
        task_id="create_indexes",
        python_callable=create_indexes,
    )
    run_quality_checks_task = PythonOperator(
        task_id="run_quality_checks",
        python_callable=run_quality_checks,
    )
    save_execution_report_task = PythonOperator(
        task_id="save_execution_report",
        python_callable=save_execution_report,
    )

    (
        validate_environment_task
        >> extract_from_pocketbase_task
        >> save_pocketbase_extract_task
        >> convert_to_parquet_task
        >> validate_parquet_schema_task
        >> transform_dimensions_task
        >> transform_fact_reservations_task
        >> load_dimensions_to_mongodb_task
        >> load_fact_to_mongodb_task
        >> create_indexes_task
        >> run_quality_checks_task
        >> save_execution_report_task
    )
