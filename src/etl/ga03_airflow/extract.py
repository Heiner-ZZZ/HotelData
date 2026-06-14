from __future__ import annotations

import hashlib
from typing import Any

import requests

from src.etl.ga03_airflow._common import auth_headers, request_with_retries, _json_default
from src.etl.ga03_airflow.config import PHASE, PIPELINE_PROGRESS_STEPS, paths, pocketbase_config
from src.etl.ga03_airflow.progress import write_pipeline_progress, write_state, _elapsed


def extract_from_pocketbase_03() -> dict[str, Any]:
    config = pocketbase_config()
    with requests.Session() as session:
        headers = auth_headers(config)
        response = request_with_retries(
            "GET",
            f"{config['base_url']}/api/collections/{config['collection']}/records",
            params={"page": 1, "perPage": 1},
            headers=headers,
            timeout=30,
        )
        payload = response.json()
    total_items = int(payload.get("totalItems", 0) or 0)
    meta_pb = int(config.get("meta_pb", 0) or 0)
    meta_mongo = int(config.get("meta_mongo", 0) or 0)
    if meta_pb > 0 and total_items != meta_pb:
        raise ValueError(f"GA03 espera {meta_pb} registros en PocketBase (META_PB), actual={total_items}")
    if meta_mongo > total_items:
        raise ValueError(
            f"GA03: META_MONGO ({meta_mongo}) no puede exceder registros en PocketBase ({total_items})"
        )
    write_pipeline_progress(
        status="running",
        section="extract",
        percent=10,
        message="Fuente PocketBase validada.",
        detail={"total_items": total_items, "expected_records": meta_pb},
    )
    report = {
        "pocketbase_url": config["base_url"],
        "collection": config["collection"],
        "total_items": total_items,
        "total_pages": payload.get("totalPages", 0),
        "page_size": config["page_size"],
    }
    write_state({"extract_plan": report})
    return report


def save_extract_jsonl_03() -> dict[str, Any]:
    all_paths = paths()
    config = pocketbase_config()
    page = 1
    records = 0
    columns: set[str] = set()
    digest = hashlib.sha256()
    temp_path = all_paths["extract_jsonl"].with_suffix(".jsonl.tmp")
    meta_mongo = int(config.get("meta_mongo", 0) or config["expected_records"] or 0)
    if all_paths["extract_jsonl"].exists():
        all_paths["extract_jsonl"].unlink()
    if temp_path.exists():
        temp_path.unlink()
    with requests.Session() as session:
        headers = auth_headers(config)
        while records < meta_mongo:
            response = request_with_retries(
                "GET",
                f"{config['base_url']}/api/collections/{config['collection']}/records",
                params={"page": page, "perPage": min(config["page_size"], meta_mongo - records)},
                headers=headers,
                timeout=60,
            )
            payload = response.json()
            items = payload.get("items", [])
            if not items:
                break
            with temp_path.open("a", encoding="utf-8") as target:
                for item in items:
                    if records >= meta_mongo:
                        break
                    columns.update(item.keys())
                    line = json.dumps(item, ensure_ascii=False, default=_json_default) + "\n"
                    target.write(line)
                    digest.update(line.encode("utf-8"))
                    records += 1
            print(f"GA03 PocketBase page {page} - registros extraidos: {records}/{meta_mongo}")
            total_pages = max(int(payload.get("totalPages") or page), 1)
            extract_percent = 10 + ((page / total_pages) * 20 if total_pages else 0)
            write_pipeline_progress(
                status="running",
                section="extract",
                percent=min(extract_percent, PIPELINE_PROGRESS_STEPS["extract"]),
                message="Extrayendo desde PocketBase.",
                detail={
                    "page": page,
                    "total_pages": total_pages,
                    "records": records,
                    "meta_mongo": meta_mongo,
                    "elapsed_ms": _elapsed(),
                },
            )
            page += 1
    if records != meta_mongo:
        raise ValueError(f"Extraccion GA03 incompleta: esperado={meta_mongo}, actual={records}")
    temp_path.replace(all_paths["extract_jsonl"])
    write_pipeline_progress(
        status="running",
        section="extract",
        percent=PIPELINE_PROGRESS_STEPS["extract"],
        message="Extracción JSONL completada.",
        detail={"records": records, "jsonl_path": str(all_paths["extract_jsonl"])},
    )
    report = {
        "records": records,
        "columns": sorted(columns),
        "jsonl_path": str(all_paths["extract_jsonl"]),
        "jsonl_sha256": digest.hexdigest(),
        "jsonl_bytes": all_paths["extract_jsonl"].stat().st_size,
        "collection": config["collection"],
        "expected_records": meta_mongo,
    }
    write_state({"extract_report": report})
    return report
