from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from pymongo import UpdateOne

from config.settings import get_settings
from src.database.connection import get_database
from src.etl.ta02_dimensions import DIMENSION_KEY_FIELDS, build_ta02_dimensions
from src.etl.ta02_fact import REQUIRED_FACT_COLUMNS, transform_fact_hotel_reservations, utc_now_iso
from src.etl.ta02_load_mongodb import (
    collection_counts,
    create_ta02_indexes,
    insert_execution_report,
    insert_quality_report,
    insert_rejected_records,
    upsert_dimensions,
)


DEFAULT_POCKETBASE_URL = "http://127.0.0.1:8090"
DEFAULT_COLLECTION = "hotel_reservation_events__2"
DEFAULT_PAGE_SIZE = 500
INSERT_BATCH_SIZE = 5000


def _paths() -> dict[str, Path]:
    settings = get_settings()
    dimension_dir = settings.processed_dir / "ta02_dimensions"
    return {
        "state": settings.staging_dir / "ta02_execution_state.json",
        "extract_jsonl": settings.staging_dir / "pocketbase_full_extract.jsonl",
        "parquet": settings.processed_dir / "hotel_reservations_full.parquet",
        "fact_jsonl": settings.processed_dir / "fact_hotel_reservations_ta02.jsonl",
        "rejected_jsonl": settings.processed_dir / "rejected_records_ta02.jsonl",
        "dimension_dir": dimension_dir,
        "quality_report": settings.reports_dir / "ta02_quality_report.json",
        "execution_report": settings.reports_dir / "ta02_execution_report.json",
    }


def _json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def _read_state() -> dict[str, Any]:
    state_path = _paths()["state"]
    if not state_path.exists():
        raise FileNotFoundError(f"No existe estado TA 02: {state_path}")
    return json.loads(state_path.read_text(encoding="utf-8"))


def _write_state(update: dict[str, Any]) -> dict[str, Any]:
    paths = _paths()
    paths["state"].parent.mkdir(parents=True, exist_ok=True)
    state = {}
    if paths["state"].exists():
        state = json.loads(paths["state"].read_text(encoding="utf-8"))
    state.update(update)
    paths["state"].write_text(json.dumps(state, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    return state


def _pocketbase_config() -> dict[str, str | int | None]:
    settings = get_settings()
    return {
        "base_url": os.getenv("POCKETBASE_URL", settings.pocketbase_url or DEFAULT_POCKETBASE_URL).rstrip("/"),
        "collection": os.getenv("POCKETBASE_COLLECTION", settings.pocketbase_collection or DEFAULT_COLLECTION),
        "page_size": int(os.getenv("POCKETBASE_PAGE_SIZE", str(DEFAULT_PAGE_SIZE))),
        "auth_token": os.getenv("POCKETBASE_AUTH_TOKEN") or settings.pocketbase_auth_token,
        "admin_email": os.getenv("POCKETBASE_ADMIN_EMAIL", "hzambranor@uteq.edu.ec"),
        "admin_password": os.getenv("POCKETBASE_ADMIN_PASSWORD", "Heiner2005*"),
    }


def _auth_headers(session: requests.Session, config: dict[str, str | int | None]) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if config.get("auth_token"):
        headers["Authorization"] = f"Bearer {config['auth_token']}"
        return headers

    email = config.get("admin_email")
    password = config.get("admin_password")
    if email and password:
        response = session.post(
            f"{config['base_url']}/api/collections/_superusers/auth-with-password",
            json={"identity": email, "password": password},
            timeout=30,
        )
        response.raise_for_status()
        headers["Authorization"] = f"Bearer {response.json()['token']}"
    return headers


def _write_jsonl(path: Path, documents: list[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as target:
        for document in documents:
            target.write(json.dumps(document, ensure_ascii=False, default=_json_default) + "\n")
    return len(documents)


def _iter_jsonl(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as source:
        for line in source:
            if line.strip():
                yield json.loads(line)


def _insert_fact_jsonl(db, path: Path, batch_size: int = INSERT_BATCH_SIZE) -> int:
    inserted = 0
    batch: list[dict[str, Any]] = []
    for document in _iter_jsonl(path):
        batch.append(document)
        if len(batch) >= batch_size:
            result = db.fact_hotel_reservations.insert_many(batch, ordered=False)
            inserted += len(result.inserted_ids)
            batch = []
            print(f"Hechos insertados: {inserted}")
    if batch:
        result = db.fact_hotel_reservations.insert_many(batch, ordered=False)
        inserted += len(result.inserted_ids)
    return inserted


def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as source:
        return sum(1 for line in source if line.strip())


def _upsert_fact_jsonl_by_source_record_id(db, path: Path, batch_size: int = INSERT_BATCH_SIZE) -> int:
    processed = 0
    operations = []
    for document in _iter_jsonl(path):
        source_record_id = document.get("source_record_id")
        if source_record_id is None:
            raise ValueError("No se puede hacer upsert del hecho sin source_record_id")
        operations.append(
            UpdateOne(
                {"source_record_id": source_record_id},
                {"$set": document},
                upsert=True,
            )
        )
        if len(operations) >= batch_size:
            db.fact_hotel_reservations.bulk_write(operations, ordered=False)
            processed += len(operations)
            operations = []
            print(f"Hechos procesados por upsert: {processed}")
    if operations:
        db.fact_hotel_reservations.bulk_write(operations, ordered=False)
        processed += len(operations)
    return processed


def validate_environment() -> dict[str, Any]:
    settings = get_settings()
    paths = _paths()
    settings.staging_dir.mkdir(parents=True, exist_ok=True)
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    paths["dimension_dir"].mkdir(parents=True, exist_ok=True)

    execution_id = f"ta02_airflow_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    loaded_at = utc_now_iso()
    for key in ["extract_jsonl", "parquet", "fact_jsonl", "rejected_jsonl", "quality_report", "execution_report"]:
        if paths[key].exists():
            paths[key].unlink()
    for dimension_file in paths["dimension_dir"].glob("*.jsonl"):
        dimension_file.unlink()

    return _write_state(
        {
            "execution_id": execution_id,
            "loaded_at": loaded_at,
            "database": settings.mongo_database,
            "paths": {name: str(path) for name, path in paths.items()},
        }
    )


def extract_from_pocketbase() -> dict[str, Any]:
    config = _pocketbase_config()
    with requests.Session() as session:
        headers = _auth_headers(session, config)
        response = session.get(
            f"{config['base_url']}/api/collections/{config['collection']}/records",
            params={"page": 1, "perPage": 1},
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
    report = {
        "pocketbase_url": config["base_url"],
        "collection": config["collection"],
        "total_items": payload.get("totalItems", 0),
        "total_pages": payload.get("totalPages", 0),
        "page_size": config["page_size"],
    }
    _write_state({"extract_plan": report})
    return report


def save_pocketbase_extract() -> dict[str, Any]:
    paths = _paths()
    config = _pocketbase_config()
    if paths["extract_jsonl"].exists():
        paths["extract_jsonl"].unlink()

    page = 1
    records = 0
    columns: set[str] = set()
    with requests.Session() as session:
        headers = _auth_headers(session, config)
        while True:
            response = session.get(
                f"{config['base_url']}/api/collections/{config['collection']}/records",
                params={"page": page, "perPage": config["page_size"]},
                headers=headers,
                timeout=60,
            )
            response.raise_for_status()
            payload = response.json()
            items = payload.get("items", [])
            if not items:
                break
            with paths["extract_jsonl"].open("a", encoding="utf-8") as target:
                for item in items:
                    columns.update(item.keys())
                    target.write(json.dumps(item, ensure_ascii=False, default=_json_default) + "\n")
                    records += 1
            print(f"PocketBase page {page}/{payload.get('totalPages')} - registros extraidos: {records}")
            if page >= int(payload.get("totalPages") or page):
                break
            page += 1

    report = {"records": records, "columns": sorted(columns), "jsonl_path": str(paths["extract_jsonl"])}
    _write_state({"extract_report": report})
    return report


def convert_to_parquet() -> dict[str, Any]:
    paths = _paths()
    if not paths["extract_jsonl"].exists():
        raise FileNotFoundError(f"No existe JSONL de extraccion: {paths['extract_jsonl']}")
    dataframe = pd.read_json(paths["extract_jsonl"], lines=True, dtype=False)
    dataframe.to_parquet(paths["parquet"], index=False)
    report = {"records": len(dataframe), "columns": list(dataframe.columns), "parquet_path": str(paths["parquet"])}
    _write_state({"parquet_report": report})
    return report


def validate_parquet_schema() -> dict[str, Any]:
    paths = _paths()
    if not paths["parquet"].exists():
        raise FileNotFoundError(f"No existe Parquet: {paths['parquet']}")
    dataframe = pd.read_parquet(paths["parquet"])
    missing = [column for column in REQUIRED_FACT_COLUMNS if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Parquet TA 02 sin columnas requeridas: {missing}")
    report = {"valid": True, "records": len(dataframe), "columns": list(dataframe.columns)}
    _write_state({"schema_report": report})
    return report


def transform_dimensions() -> dict[str, int]:
    paths = _paths()
    state = _read_state()
    dataframe = pd.read_parquet(paths["parquet"])
    _, _, valid_fact_frame = transform_fact_hotel_reservations(
        dataframe,
        state["execution_id"],
        state["loaded_at"],
    )
    dimensions = build_ta02_dimensions(valid_fact_frame, state["loaded_at"])
    counts = {}
    for collection_name, documents in dimensions.items():
        counts[collection_name] = _write_jsonl(paths["dimension_dir"] / f"{collection_name}.jsonl", documents)
    _write_state({"dimension_counts": counts})
    return counts


def transform_fact_reservations() -> dict[str, int]:
    paths = _paths()
    state = _read_state()
    dataframe = pd.read_parquet(paths["parquet"])
    facts, rejected, _ = transform_fact_hotel_reservations(dataframe, state["execution_id"], state["loaded_at"])
    fact_count = _write_jsonl(paths["fact_jsonl"], facts)
    rejected_count = _write_jsonl(paths["rejected_jsonl"], rejected)
    report = {"fact_hotel_reservations": fact_count, "rejected_records": rejected_count}
    _write_state({"fact_transform_counts": report})
    return report


def load_dimensions_to_mongodb() -> dict[str, int]:
    paths = _paths()
    dimensions: dict[str, list[dict[str, Any]]] = {}
    for collection_name in DIMENSION_KEY_FIELDS:
        dimensions[collection_name] = list(_iter_jsonl(paths["dimension_dir"] / f"{collection_name}.jsonl") or [])
    counts = upsert_dimensions(get_database(), dimensions)
    _write_state({"dimension_load_counts": counts})
    return counts


def load_fact_to_mongodb() -> dict[str, int]:
    paths = _paths()
    db = get_database()
    settings = get_settings()
    full_reload = settings.full_reload or os.getenv("TA02_FULL_RELOAD_FACTS", "true").lower() == "true"
    previous_count = db.fact_hotel_reservations.count_documents({})
    expected_new_count = _count_jsonl(paths["fact_jsonl"])
    deleted = 0

    print(f"Conteo anterior de fact_hotel_reservations: {previous_count}")
    print(f"Full reload de hechos habilitado: {full_reload}")
    print(f"Conteo final esperado de fact_hotel_reservations: {expected_new_count if full_reload else 'sin duplicados por upsert'}")

    if full_reload:
        deleted = db.fact_hotel_reservations.delete_many({}).deleted_count
        print(f"Limpieza ejecutada sobre fact_hotel_reservations: {deleted} documentos borrados")
        fact_count = _insert_fact_jsonl(db, paths["fact_jsonl"])
    else:
        print("Limpieza no ejecutada. Se usara upsert por source_record_id para evitar duplicados.")
        db.fact_hotel_reservations.create_index("source_record_id")
        fact_count = _upsert_fact_jsonl_by_source_record_id(db, paths["fact_jsonl"])

    final_count = db.fact_hotel_reservations.count_documents({})
    print(f"Conteo final de fact_hotel_reservations: {final_count}")
    if full_reload and final_count != expected_new_count:
        raise RuntimeError(
            "Conteo final inesperado en fact_hotel_reservations: "
            f"esperado={expected_new_count}, actual={final_count}"
        )

    rejected = list(_iter_jsonl(paths["rejected_jsonl"]) or [])
    rejected_count = insert_rejected_records(db, rejected)
    counts = {
        "previous_fact_hotel_reservations": previous_count,
        "deleted_facts_before_load": deleted,
        "fact_hotel_reservations": fact_count,
        "expected_fact_hotel_reservations": expected_new_count,
        "final_fact_hotel_reservations": final_count,
        "rejected_records": rejected_count,
    }
    _write_state({"fact_load_counts": counts})
    return counts


def create_indexes() -> dict[str, list[str]]:
    result = create_ta02_indexes(get_database())
    _write_state({"indexes": result})
    return result


def run_quality_checks() -> dict[str, Any]:
    paths = _paths()
    state = _read_state()
    schema = state.get("schema_report", {})
    fact_counts = state.get("fact_transform_counts", {})
    dimension_counts = state.get("dimension_counts", {})
    source_rows = int(schema.get("records", 0) or 0)
    valid_records = int(fact_counts.get("fact_hotel_reservations", 0) or 0)
    rejected_records = int(fact_counts.get("rejected_records", 0) or 0)
    report = {
        "execution_id": state["execution_id"],
        "generated_at": utc_now_iso(),
        "source": str(paths["parquet"]),
        "source_rows": source_rows,
        "valid_fact_records": valid_records,
        "rejected_records": rejected_records,
        "completeness_score": round(valid_records / source_rows, 4) if source_rows else 0,
        "dimensions": dimension_counts,
        "schema": schema,
        "extract": state.get("extract_report", {}),
        "parquet": state.get("parquet_report", {}),
    }
    paths["quality_report"].write_text(json.dumps(report, indent=2, ensure_ascii=False, default=_json_default), encoding="utf-8")
    _write_state({"quality_report": report})
    return report


def save_execution_report() -> dict[str, Any]:
    paths = _paths()
    state = _read_state()
    db = get_database()
    collections = [
        *DIMENSION_KEY_FIELDS.keys(),
        "fact_hotel_reservations",
        "rejected_records",
        "etl_executions",
        "data_quality_reports",
    ]
    final_counts = collection_counts(db, collections)
    execution_report = {
        "execution_id": state["execution_id"],
        "executed_at": state["loaded_at"],
        "status": "success",
        "database": state["database"],
        "source": str(paths["parquet"]),
        "loaded_collections": {
            **state.get("dimension_load_counts", {}),
            **state.get("fact_load_counts", {}),
        },
        "final_counts": final_counts,
    }
    quality_report = state.get("quality_report")
    if quality_report is None:
        raise RuntimeError("No existe quality_report en estado. Ejecute run_quality_checks antes.")
    insert_quality_report(db, quality_report)
    insert_execution_report(db, execution_report)
    paths["execution_report"].write_text(
        json.dumps(execution_report, indent=2, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )
    _write_state({"execution_report": execution_report})
    return {
        "status": "success",
        "execution_id": state["execution_id"],
        "report_saved": True,
    }
