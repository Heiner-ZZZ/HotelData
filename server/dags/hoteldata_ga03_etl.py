from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator

PROJECT_ROOT = Path(os.getenv("HOTELDATA_PROJECT_ROOT", "/opt/hoteldata"))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.etl.ga03_airflow import (
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


def _load_infra_env() -> dict[str, str]:
    env_path = PROJECT_ROOT / "infra" / "docker" / ".env"
    overrides: dict[str, str] = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                overrides[key.strip()] = val.strip()
    return overrides


def _run_script(script_name: str, extra_args: list[str] | None = None) -> None:
    script_path = PROJECT_ROOT / "scripts" / script_name
    cmd = [sys.executable, str(script_path), *(extra_args or [])]
    env = {**os.environ, **_load_infra_env()}
    result = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=7200,
        env=env,
    )
    if result.returncode != 0:
        msg = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"{script_name} failed (rc={result.returncode}): {msg}")


def seed_source() -> None:
    import requests
    env = _load_infra_env()
    pb_url = env.get("POCKETBASE_URL", "http://pocketbase:8090")
    pb_email = env.get("POCKETBASE_ADMIN_EMAIL", "hzambranor@uteq.edu.ec")
    pb_pass = env.get("POCKETBASE_ADMIN_PASSWORD", "Heiner2005*")
    expected = int(env.get("TARGET_RECORDS", env.get("GA03_EXPECTED_RECORDS", "800000")))
    try:
        auth = requests.post(
            f"{pb_url}/api/collections/_superusers/auth-with-password",
            json={"identity": pb_email, "password": pb_pass}, timeout=30,
        )
        token = auth.json().get("token", "")
        r = requests.get(
            f"{pb_url}/api/collections/hotel_reservation_events_03/records?perPage=1",
            headers={"Authorization": f"Bearer {token}"}, timeout=30,
        )
        current = r.json().get("totalItems", 0)
    except Exception:
        current = 0
    if current >= expected:
        print(f"seed_source: PocketBase ya tiene {current}/{expected} registros. Omitiendo seed.")
        return
    csv_path = PROJECT_ROOT / "data" / "uploads" / "ga03_source.csv"
    print(f"seed_source: PocketBase vacío. Sembrando {expected} registros desde CSV...")
    _run_script("cargar_reservas_hoteleras_03.py", ["--csv", str(csv_path), "--target", str(expected), "--reload", "--confirm-reload", "hotel_reservation_events_03"])


def validate_dataset() -> None:
    _run_script("validar_dataset_reservas_03.py")


with DAG(
    dag_id="hoteldata_ga03_etl",
    description="GA03 ETL completo: seed (CSV→PocketBase) → validación → pipeline (PocketBase→Parquet→MongoDB)",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["hoteldata-hub", "ga03", "reservas", "mongodb", "parquet", "etl"],
) as dag:
    seed_source_task = PythonOperator(
        task_id="seed_source",
        python_callable=seed_source,
    )
    validate_dataset_task = PythonOperator(
        task_id="validate_dataset",
        python_callable=validate_dataset,
    )
    validate_environment_task = PythonOperator(
        task_id="validate_environment",
        python_callable=validate_environment_03,
    )
    extract_from_pocketbase_task = PythonOperator(
        task_id="extract_from_pocketbase",
        python_callable=extract_from_pocketbase_03,
    )
    save_extract_jsonl_task = PythonOperator(
        task_id="save_extract_jsonl",
        python_callable=save_extract_jsonl_03,
    )
    convert_to_parquet_task = PythonOperator(
        task_id="convert_to_parquet",
        python_callable=convert_to_parquet_03,
    )
    validate_parquet_schema_task = PythonOperator(
        task_id="validate_parquet_schema",
        python_callable=validate_parquet_schema_03,
    )
    transform_dimensions_task = PythonOperator(
        task_id="transform_dimensions",
        python_callable=transform_dimensions_03,
    )
    transform_fact_reservations_task = PythonOperator(
        task_id="transform_fact_reservations",
        python_callable=transform_fact_reservations_03,
    )
    load_dimensions_to_mongodb_task = PythonOperator(
        task_id="load_dimensions_to_mongodb",
        python_callable=load_dimensions_to_mongodb_03,
    )
    load_fact_to_mongodb_task = PythonOperator(
        task_id="load_fact_to_mongodb",
        python_callable=load_fact_to_mongodb_03,
    )
    create_indexes_task = PythonOperator(
        task_id="create_indexes",
        python_callable=create_indexes_03,
    )
    run_quality_checks_task = PythonOperator(
        task_id="run_quality_checks",
        python_callable=run_quality_checks_03,
    )
    save_execution_report_task = PythonOperator(
        task_id="save_execution_report",
        python_callable=save_execution_report_03,
    )

    (
        seed_source_task
        >> validate_dataset_task
        >> validate_environment_task
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
