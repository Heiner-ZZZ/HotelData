from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv


SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))
PROJECT_ROOT = Path(__file__).resolve().parents[2]

from config.settings import get_settings
from src.database.connection import get_database
from src.etl.ta02_dimensions import DIMENSION_KEY_FIELDS, build_ta02_dimensions
from src.etl.ta02_fact import transform_fact_hotel_reservations, utc_now_iso
from src.etl.ta02_load_mongodb import (
    collection_counts,
    create_ta02_indexes,
    insert_execution_report,
    insert_quality_report,
    insert_rejected_records,
    upsert_dimensions,
)


load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_POCKETBASE_URL = "http://127.0.0.1:8090"
DEFAULT_COLLECTION = "hotel_reservation_events__2"
DEFAULT_PAGE_SIZE = 500
INSERT_BATCH_SIZE = 5000

STAGING_JSONL = PROJECT_ROOT / "data" / "staging" / "pocketbase_full_extract.jsonl"
FULL_PARQUET = PROJECT_ROOT / "data" / "processed" / "hotel_reservations_full.parquet"


def new_execution_id() -> str:
    return f"ta02_full_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"


def get_pocketbase_config() -> dict[str, str | int | None]:
    return {
        "base_url": os.getenv("POCKETBASE_URL", DEFAULT_POCKETBASE_URL).rstrip("/"),
        "collection": os.getenv("POCKETBASE_COLLECTION", DEFAULT_COLLECTION),
        "page_size": int(os.getenv("POCKETBASE_PAGE_SIZE", str(DEFAULT_PAGE_SIZE))),
        "auth_token": os.getenv("POCKETBASE_AUTH_TOKEN"),
        "admin_email": os.getenv("POCKETBASE_ADMIN_EMAIL", "hzambranor@uteq.edu.ec"),
        "admin_password": os.getenv("POCKETBASE_ADMIN_PASSWORD", "Heiner2005*"),
    }


def authenticate_if_needed(session: requests.Session, config: dict[str, str | int | None]) -> dict[str, str]:
    if config.get("auth_token"):
        return {"Authorization": f"Bearer {config['auth_token']}"}

    email = config.get("admin_email")
    password = config.get("admin_password")
    if not email or not password:
        return {}

    auth_url = f"{config['base_url']}/api/collections/_superusers/auth-with-password"
    response = session.post(auth_url, json={"identity": email, "password": password}, timeout=30)
    response.raise_for_status()
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def extract_all_from_pocketbase() -> dict[str, Any]:
    config = get_pocketbase_config()
    STAGING_JSONL.parent.mkdir(parents=True, exist_ok=True)
    if STAGING_JSONL.exists():
        STAGING_JSONL.unlink()

    total_written = 0
    detected_columns: set[str] = set()
    page = 1

    with requests.Session() as session:
        headers = {"Accept": "application/json", **authenticate_if_needed(session, config)}

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

            with STAGING_JSONL.open("a", encoding="utf-8") as target:
                for item in items:
                    detected_columns.update(item.keys())
                    target.write(json.dumps(item, ensure_ascii=False) + "\n")
                    total_written += 1

            print(f"PocketBase page {page}/{payload.get('totalPages')} - registros extraidos: {total_written}")
            if page >= int(payload.get("totalPages") or page):
                break
            page += 1

    return {
        "source": "pocketbase",
        "collection": config["collection"],
        "jsonl_path": str(STAGING_JSONL),
        "records": total_written,
        "columns": sorted(detected_columns),
    }


def convert_jsonl_to_parquet() -> dict[str, Any]:
    if not STAGING_JSONL.exists():
        raise FileNotFoundError(f"No existe la extraccion JSONL: {STAGING_JSONL}")

    FULL_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    dataframe = pd.read_json(STAGING_JSONL, lines=True, dtype=False)
    dataframe.to_parquet(FULL_PARQUET, index=False)
    return {
        "parquet_path": str(FULL_PARQUET),
        "records": len(dataframe),
        "columns": list(dataframe.columns),
    }


def insert_facts_in_batches(db, facts: list[dict[str, Any]], batch_size: int = INSERT_BATCH_SIZE) -> int:
    inserted = 0
    for start in range(0, len(facts), batch_size):
        batch = facts[start:start + batch_size]
        if not batch:
            continue
        result = db.fact_hotel_reservations.insert_many(batch, ordered=False)
        inserted += len(result.inserted_ids)
        print(f"Hechos insertados: {inserted}/{len(facts)}")
    return inserted


def controlled_fact_reload(db) -> int:
    full_reload = os.getenv("TA02_FULL_RELOAD_FACTS", "true").lower() == "true"
    if not full_reload:
        print("TA02_FULL_RELOAD_FACTS=false: no se borra fact_hotel_reservations antes de cargar.")
        return 0
    result = db.fact_hotel_reservations.delete_many({})
    print(f"Full reload controlado: fact_hotel_reservations borrados: {result.deleted_count}")
    return result.deleted_count


def main() -> None:
    settings = get_settings()
    db = get_database()
    run_id = new_execution_id()
    loaded_at = utc_now_iso()

    print(f"execution_id: {run_id}")
    print("1. Extrayendo TODOS los registros desde PocketBase...")
    extract_report = extract_all_from_pocketbase()

    print("2. Convirtiendo JSONL completo a Parquet...")
    parquet_report = convert_jsonl_to_parquet()

    print("3. Leyendo Parquet completo...")
    dataframe = pd.read_parquet(FULL_PARQUET)
    print(f"Filas leidas desde Parquet: {len(dataframe)}")

    print("4. Transformando tabla de hechos...")
    facts, rejected, valid_fact_frame = transform_fact_hotel_reservations(dataframe, run_id, loaded_at)

    print("5. Transformando dimensiones...")
    dimensions = build_ta02_dimensions(valid_fact_frame, loaded_at)

    print("6. Creando indices...")
    create_ta02_indexes(db)

    print("7. Cargando dimensiones con upsert...")
    dimension_counts = upsert_dimensions(db, dimensions)

    print("8. Cargando fact_hotel_reservations...")
    deleted_facts = controlled_fact_reload(db)
    fact_count = insert_facts_in_batches(db, facts)

    print("9. Guardando rejected_records si existen...")
    rejected_count = insert_rejected_records(db, rejected)

    source_rows = len(dataframe)
    quality_report = {
        "execution_id": run_id,
        "generated_at": loaded_at,
        "source": str(FULL_PARQUET),
        "pocketbase_extract": extract_report,
        "parquet": parquet_report,
        "source_rows": source_rows,
        "valid_fact_records": len(facts),
        "rejected_records": len(rejected),
        "completeness_score": round(len(facts) / source_rows, 4) if source_rows else 0,
        "dimensions": {name: len(items) for name, items in dimensions.items()},
    }
    execution_report = {
        "execution_id": run_id,
        "executed_at": loaded_at,
        "status": "success",
        "database": settings.mongo_database,
        "source": str(FULL_PARQUET),
        "deleted_facts_before_load": deleted_facts,
        "loaded_collections": {
            **dimension_counts,
            "fact_hotel_reservations": fact_count,
            "rejected_records": rejected_count,
        },
    }

    print("10. Guardando data_quality_reports...")
    insert_quality_report(db, quality_report)

    print("11. Guardando etl_executions...")
    insert_execution_report(db, execution_report)

    collections = [
        *DIMENSION_KEY_FIELDS.keys(),
        "fact_hotel_reservations",
        "rejected_records",
        "etl_executions",
        "data_quality_reports",
    ]
    final_counts = collection_counts(db, collections)

    print("\nPipeline TA 02 completo finalizado.")
    print("Conteos cargados en esta ejecucion:")
    print(json.dumps(execution_report["loaded_collections"], indent=2, ensure_ascii=False))
    print("Conteos finales por coleccion:")
    print(json.dumps(final_counts, indent=2, ensure_ascii=False))
    print(f"execution_id: {run_id}")


if __name__ == "__main__":
    main()
