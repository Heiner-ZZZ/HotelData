from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import requests

from config.settings import get_settings
from src.etl.ta02_airflow_tasks._state import (
    _auth_headers,
    _iter_jsonl,
    _json_default,
    _paths,
    _pocketbase_config,
    _write_state,
)
from src.etl.ta02_fact import utc_now_iso


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
