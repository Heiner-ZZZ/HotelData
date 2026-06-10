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

from src.etl.ga03_airflow_tasks import (
    convert_to_parquet_03,
    create_indexes_03,
    extract_from_pocketbase_03,
    load_dimensions_to_mongodb_03,
    load_fact_to_mongodb_03,
    run_quality_checks_03,
    save_execution_report_03,
    save_extract_jsonl_03,
    transform_dimensions_03,
    transform_fact_reservations_03,
    validate_environment_03,
    validate_parquet_schema_03,
)


with DAG(
    dag_id="hoteldata_reservas_03_pipeline",
    description="GA03 HotelData reservas: PocketBase to Parquet to MongoDB",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["hoteldata-hub", "ga03", "reservas", "mongodb", "parquet"],
) as dag:
    validate_environment_task = PythonOperator(task_id="validate_environment_03", python_callable=validate_environment_03)
    extract_from_pocketbase_task = PythonOperator(task_id="extract_from_pocketbase_03", python_callable=extract_from_pocketbase_03)
    save_extract_jsonl_task = PythonOperator(task_id="save_extract_jsonl_03", python_callable=save_extract_jsonl_03)
    convert_to_parquet_task = PythonOperator(task_id="convert_to_parquet_03", python_callable=convert_to_parquet_03)
    validate_parquet_schema_task = PythonOperator(task_id="validate_parquet_schema_03", python_callable=validate_parquet_schema_03)
    transform_dimensions_task = PythonOperator(task_id="transform_dimensions_03", python_callable=transform_dimensions_03)
    transform_fact_reservations_task = PythonOperator(task_id="transform_fact_reservations_03", python_callable=transform_fact_reservations_03)
    load_dimensions_to_mongodb_task = PythonOperator(task_id="load_dimensions_to_mongodb_03", python_callable=load_dimensions_to_mongodb_03)
    load_fact_to_mongodb_task = PythonOperator(task_id="load_fact_to_mongodb_03", python_callable=load_fact_to_mongodb_03)
    create_indexes_task = PythonOperator(task_id="create_indexes_03", python_callable=create_indexes_03)
    run_quality_checks_task = PythonOperator(task_id="run_quality_checks_03", python_callable=run_quality_checks_03)
    save_execution_report_task = PythonOperator(task_id="save_execution_report_03", python_callable=save_execution_report_03)

    (
        validate_environment_task
        >> extract_from_pocketbase_task
        >> save_extract_jsonl_task
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
