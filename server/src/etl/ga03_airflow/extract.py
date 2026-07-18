from __future__ import annotations

import hashlib
import json
from typing import Any

from src.etl.ga03_airflow._common import auth_headers, request_with_retries, _json_default
from src.etl.ga03_airflow.config import PIPELINE_PROGRESS_STEPS, paths, pocketbase_config
from src.etl.ga03_airflow.progress import write_pipeline_progress, write_state, read_state, _elapsed


def extract_from_pocketbase_03() -> dict[str, Any]:
    config = pocketbase_config()
    state = read_state()
    incremental = config["incremental_mode"] and state.get("last_extracted_at")
    headers = auth_headers(config)
    params: dict[str, Any] = {"page": 1, "perPage": 1}
    if incremental:
        params["filter"] = f"(created>'{state['last_extracted_at']}')"
        params["sort"] = "created"
    response = request_with_retries(
        "GET",
        f"{config['base_url']}/api/collections/{config['collection']}/records",
        params=params,
        headers=headers,
        timeout=30,
    )
    payload = response.json()
    total_items = int(payload.get("totalItems", 0) or 0)
    min_expected = int(config.get("expected_records", 0) or 0)
    if incremental:
        actual_expected = total_items
        print(f"GA03 incremental: {total_items} registros desde HWM (minimo configurado={min_expected})")
    else:
        if total_items < min_expected:
            raise ValueError(f"GA03 requiere minimo {min_expected} registros en PocketBase, actual={total_items}")
        actual_expected = max(total_items, min_expected)
        if total_items > min_expected:
            print(f"GA03 PocketBase tiene {total_items} registros, procesando todos (minimo configurado={min_expected})")
    write_pipeline_progress(
        status="running",
        section="extract",
        percent=10,
        message=f"Fuente PocketBase validada{' (incremental)' if incremental else ''}.",
        detail={"total_items": total_items, "min_expected": min_expected, "actual_expected": actual_expected, "incremental": incremental},
    )
    write_state({"expected_records": actual_expected})
    report = {
        "pocketbase_url": config["base_url"],
        "collection": config["collection"],
        "total_items": total_items,
        "total_pages": payload.get("totalPages", 0),
        "page_size": config["page_size"],
        "expected_records": actual_expected,
        "incremental": incremental,
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
    state = read_state()
    incremental = config["incremental_mode"] and state.get("last_extracted_at")
    expected = int(state.get("expected_records", config.get("expected_records", 0) or 0))
    max_created: str | None = None
    if all_paths["extract_jsonl"].exists():
        all_paths["extract_jsonl"].unlink()
    if temp_path.exists():
        temp_path.unlink()
    headers = auth_headers(config)
    while records < expected:
        params: dict[str, Any] = {"page": page, "perPage": min(config["page_size"], expected - records)}
        if incremental:
            params["filter"] = f"(created>'{state['last_extracted_at']}')"
            params["sort"] = "created"
        response = request_with_retries(
            "GET",
            f"{config['base_url']}/api/collections/{config['collection']}/records",
            params=params,
            headers=headers,
            timeout=60,
        )
        payload = response.json()
        items = payload.get("items", [])
        if not items:
            break
        with temp_path.open("a", encoding="utf-8") as target:
            for item in items:
                if records >= expected:
                    break
                columns.update(item.keys())
                line = json.dumps(item, ensure_ascii=False, default=_json_default) + "\n"
                target.write(line)
                digest.update(line.encode("utf-8"))
                records += 1
                created = item.get("created")
                if created and (max_created is None or created > max_created):
                    max_created = created
        print(f"GA03 PocketBase page {page} - registros extraidos: {records}/{expected}")
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
                "expected_records": expected,
                "incremental": incremental,
                "elapsed_ms": _elapsed(),
            },
        )
        page += 1
    if records != expected:
        raise ValueError(f"Extraccion GA03 incompleta: esperado={expected}, actual={records}")
    temp_path.replace(all_paths["extract_jsonl"])
    if incremental and max_created:
        write_state({"last_extracted_at": max_created})
        print(f"GA03 HWM actualizado: {max_created}")
    write_pipeline_progress(
        status="running",
        section="extract",
        percent=PIPELINE_PROGRESS_STEPS["extract"],
        message="Extracción JSONL completada.",
        detail={"records": records, "jsonl_path": str(all_paths["extract_jsonl"]), "incremental": incremental},
    )
    report = {
        "records": records,
        "columns": sorted(columns),
        "jsonl_path": str(all_paths["extract_jsonl"]),
        "jsonl_sha256": digest.hexdigest(),
        "jsonl_bytes": all_paths["extract_jsonl"].stat().st_size,
        "collection": config["collection"],
        "expected_records": expected,
        "incremental": incremental,
    }
    write_state({"extract_report": report})
    return report
