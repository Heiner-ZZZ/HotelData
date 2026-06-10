from __future__ import annotations

import json
import os
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from pymongo import UpdateOne

from config.settings import get_settings
from src.database.connection import get_database
from src.etl.ga03_audit import (
    build_execution_report,
    build_quality_report,
    insert_ga03_reports,
    json_default,
    utc_now_iso,
    write_json_report,
)
from src.etl.ta02_dimensions import DIMENSION_KEY_FIELDS, build_ta02_dimensions
from src.etl.ta02_fact import REQUIRED_FACT_COLUMNS, transform_fact_hotel_reservations
from src.etl.ta02_load_mongodb import collection_counts, create_ta02_indexes, upsert_dimensions


PHASE = "GA03"
INSERT_BATCH_SIZE = 5000
PIPELINE_PROGRESS_STEPS = {
    "environment": 5,
    "extract": 30,
    "parquet": 45,
    "transform": 65,
    "load_mongodb": 88,
    "reports": 100,
}
PIPELINE_STARTED_MONO: float | None = None


def paths() -> dict[str, Path]:
    settings = get_settings()
    dimension_dir = settings.processed_dir / "ga03_dimensions"
    return {
        "state": settings.staging_dir / "ga03_execution_state.json",
        "extract_jsonl": settings.staging_dir / "reservas_hoteleras_03_extract.jsonl",
        "parquet": settings.processed_dir / "reservas_hoteleras_03.parquet",
        "fact_jsonl": settings.processed_dir / "fact_hotel_reservations_ga03.jsonl",
        "rejected_jsonl": settings.processed_dir / "rejected_records_ga03.jsonl",
        "dimension_dir": dimension_dir,
        "parquet_meta": settings.processed_dir / "reservas_hoteleras_03.parquet.meta.json",
        "fact_meta": settings.processed_dir / "fact_hotel_reservations_ga03.meta.json",
        "quality_report": settings.reports_dir / "reporte_calidad_reservas_03.json",
        "execution_report": settings.reports_dir / "reporte_ejecucion_reservas_03.json",
        "pipeline_progress": settings.reports_dir / "progreso_pipeline_reservas_03.json",
    }


def _elapsed_ms() -> int:
    if PIPELINE_STARTED_MONO is None:
        return 0
    return int((time.perf_counter() - PIPELINE_STARTED_MONO) * 1000)


def _write_pipeline_progress(
    *,
    status: str,
    section: str,
    percent: float,
    message: str,
    detail: dict[str, Any] | None = None,
) -> None:
    progress_path = paths()["pipeline_progress"]
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "task_number": "03",
        "status": status,
        "section": section,
        "percent": round(percent, 2),
        "elapsed_ms": _elapsed_ms(),
        "message": message,
        "detail": detail or {},
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "sections": {
            "extract": {"label": "Extract", "complete": percent >= PIPELINE_PROGRESS_STEPS["extract"]},
            "parquet": {"label": "Parquet", "complete": percent >= PIPELINE_PROGRESS_STEPS["parquet"]},
            "transform": {"label": "Transform", "complete": percent >= PIPELINE_PROGRESS_STEPS["transform"]},
            "load_mongodb": {"label": "Carga MongoDB", "complete": percent >= PIPELINE_PROGRESS_STEPS["load_mongodb"]},
            "reports": {"label": "Reportes", "complete": percent >= PIPELINE_PROGRESS_STEPS["reports"]},
        },
    }
    progress_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=json_default), encoding="utf-8")


def _write_state(update: dict[str, Any]) -> dict[str, Any]:
    state_path = paths()["state"]
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state: dict[str, Any] = {}
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
    state.update(update)
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False, default=json_default), encoding="utf-8")
    return state


def _read_state() -> dict[str, Any]:
    state_path = paths()["state"]
    if not state_path.exists():
        raise FileNotFoundError(f"No existe estado GA03: {state_path}")
    return json.loads(state_path.read_text(encoding="utf-8"))


def _pocketbase_config() -> dict[str, str | int | None]:
    settings = get_settings()
    meta_pb = int(os.getenv("META_PB", os.getenv("TARGET_RECORDS", str(settings.target_records))))
    meta_mongo = int(os.getenv("META_MONGO", os.getenv("TARGET_RECORDS", str(settings.target_records))))
    return {
        "base_url": os.getenv("POCKETBASE_URL", settings.pocketbase_url).rstrip("/"),
        "collection": os.getenv("POCKETBASE_COLLECTION_03", settings.pocketbase_collection_03),
        "page_size": int(os.getenv("POCKETBASE_PAGE_SIZE", str(settings.pocketbase_page_size))),
        "auth_token": os.getenv("POCKETBASE_AUTH_TOKEN") or settings.pocketbase_auth_token,
        "admin_email": os.getenv("POCKETBASE_ADMIN_EMAIL"),
        "admin_password": os.getenv("POCKETBASE_ADMIN_PASSWORD"),
        "task_number": os.getenv("TASK_NUMBER", settings.task_number),
        "expected_records": meta_mongo,
        "meta_pb": meta_pb,
        "meta_mongo": meta_mongo,
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


def _request_with_retries(method: str, url: str, *, retries: int = 3, **kwargs):
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            response = requests.request(method, url, timeout=kwargs.pop("timeout", 60), **kwargs)
            response.raise_for_status()
            return response
        except Exception as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Fallo request {method} {url}: {last_error}") from last_error


def _iter_jsonl(path: Path):
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as source:
        for line in source:
            if line.strip():
                yield json.loads(line)


def _write_jsonl(path: Path, documents: list[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as target:
        for document in documents:
            target.write(json.dumps(document, ensure_ascii=False, default=json_default) + "\n")
    return len(documents)


def _count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as source:
        return sum(1 for line in source if line.strip())


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=json_default), encoding="utf-8")


def _reuse_existing_dimensions_enabled() -> bool:
    return os.getenv("GA03_REUSE_EXISTING_DIMENSIONS", "true").strip().lower() in {"1", "true", "yes", "on"}


def _dimension_collection_counts(db) -> dict[str, int]:
    return {collection_name: db[collection_name].count_documents({}) for collection_name in DIMENSION_KEY_FIELDS}


def _existing_dimensions_ready(db) -> tuple[bool, dict[str, int]]:
    counts = _dimension_collection_counts(db)
    ready = bool(counts) and all(count > 0 for count in counts.values())
    return ready, counts


def _insert_fact_jsonl(db, path: Path, batch_size: int = INSERT_BATCH_SIZE) -> int:
    inserted = 0
    batch: list[dict[str, Any]] = []
    expected = int(_read_state().get("expected_records", 0) or 0)
    for document in _iter_jsonl(path):
        document["phase"] = PHASE
        batch.append(document)
        if len(batch) >= batch_size:
            result = db.fact_hotel_reservations.insert_many(batch, ordered=False)
            inserted += len(result.inserted_ids)
            batch = []
            print(f"GA03 hechos insertados: {inserted}")
            load_percent = 76 + ((inserted / expected) * 12 if expected else 0)
            _write_pipeline_progress(
                status="running",
                section="load_mongodb",
                percent=min(load_percent, PIPELINE_PROGRESS_STEPS["load_mongodb"]),
                message="Cargando hecho en MongoDB.",
                detail={"inserted": inserted, "expected_records": expected, "elapsed_ms": _elapsed_ms()},
            )
    if batch:
        result = db.fact_hotel_reservations.insert_many(batch, ordered=False)
        inserted += len(result.inserted_ids)
        _write_pipeline_progress(
            status="running",
            section="load_mongodb",
            percent=PIPELINE_PROGRESS_STEPS["load_mongodb"],
            message="Cargando hecho en MongoDB.",
            detail={"inserted": inserted, "expected_records": expected, "elapsed_ms": _elapsed_ms()},
        )
    return inserted


def _upsert_fact_jsonl_by_source_record_id(db, path: Path, batch_size: int = INSERT_BATCH_SIZE) -> int:
    processed = 0
    operations: list[UpdateOne] = []
    for document in _iter_jsonl(path):
        source_record_id = document.get("source_record_id")
        if source_record_id is None:
            raise ValueError("GA03 no puede hacer upsert sin source_record_id")
        document["phase"] = PHASE
        operations.append(UpdateOne({"source_record_id": source_record_id}, {"$set": document}, upsert=True))
        if len(operations) >= batch_size:
            db.fact_hotel_reservations.bulk_write(operations, ordered=False)
            processed += len(operations)
            operations = []
            print(f"GA03 hechos procesados por upsert: {processed}")
    if operations:
        db.fact_hotel_reservations.bulk_write(operations, ordered=False)
        processed += len(operations)
    return processed


def validate_environment_03() -> dict[str, Any]:
    settings = get_settings()
    config = _pocketbase_config()
    all_paths = paths()
    settings.staging_dir.mkdir(parents=True, exist_ok=True)
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    all_paths["dimension_dir"].mkdir(parents=True, exist_ok=True)
    for key in ["quality_report", "execution_report"]:
        if all_paths[key].exists():
            all_paths[key].unlink()
    if all_paths["pipeline_progress"].exists():
        all_paths["pipeline_progress"].unlink()
    for dimension_file in all_paths["dimension_dir"].glob("*.jsonl"):
        dimension_file.unlink()
    started_at = utc_now_iso()
    meta_mongo = int(config.get("meta_mongo", 0) or config["expected_records"] or 0)
    state = {
        "execution_id": f"ga03_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "phase": PHASE,
        "task_number": config["task_number"],
        "started_at": started_at,
        "loaded_at": started_at,
        "database": settings.mongo_database,
        "expected_records": meta_mongo,
        "meta_pb": config.get("meta_pb", 0),
        "meta_mongo": meta_mongo,
        "paths": {name: str(path) for name, path in all_paths.items()},
    }
    _write_pipeline_progress(
        status="running",
        section="environment",
        percent=PIPELINE_PROGRESS_STEPS["environment"],
        message="Entorno GA03 validado.",
        detail={"database": settings.mongo_database, "meta_mongo": meta_mongo},
    )
    return _write_state(state)


def extract_from_pocketbase_03() -> dict[str, Any]:
    config = _pocketbase_config()
    with requests.Session() as session:
        headers = _auth_headers(session, config)
        response = _request_with_retries(
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
    _write_pipeline_progress(
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
    _write_state({"extract_plan": report})
    return report


def save_extract_jsonl_03() -> dict[str, Any]:
    all_paths = paths()
    config = _pocketbase_config()
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
        headers = _auth_headers(session, config)
        while records < meta_mongo:
            response = _request_with_retries(
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
                    line = json.dumps(item, ensure_ascii=False, default=json_default) + "\n"
                    target.write(line)
                    digest.update(line.encode("utf-8"))
                    records += 1
            print(f"GA03 PocketBase page {page} - registros extraidos: {records}/{meta_mongo}")
            total_pages = max(int(payload.get("totalPages") or page), 1)
            extract_percent = 10 + ((page / total_pages) * 20 if total_pages else 0)
            _write_pipeline_progress(
                status="running",
                section="extract",
                percent=min(extract_percent, PIPELINE_PROGRESS_STEPS["extract"]),
                message="Extrayendo desde PocketBase.",
                detail={
                    "page": page,
                    "total_pages": total_pages,
                    "records": records,
                    "meta_mongo": meta_mongo,
                    "elapsed_ms": _elapsed_ms(),
                },
            )
            page += 1
    if records != meta_mongo:
        raise ValueError(f"Extraccion GA03 incompleta: esperado={meta_mongo}, actual={records}")
    temp_path.replace(all_paths["extract_jsonl"])
    _write_pipeline_progress(
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
    _write_state({"extract_report": report})
    return report


def convert_to_parquet_03() -> dict[str, Any]:
    all_paths = paths()
    if not all_paths["extract_jsonl"].exists():
        raise FileNotFoundError(f"No existe JSONL GA03: {all_paths['extract_jsonl']}")
    state = _read_state()
    expected = int(state["expected_records"])
    extract_report = state.get("extract_report", {})
    parquet_meta = _read_json_file(all_paths["parquet_meta"])
    parquet_cache_valid = (
        all_paths["parquet"].exists()
        and parquet_meta.get("jsonl_sha256") == extract_report.get("jsonl_sha256")
        and int(parquet_meta.get("records", 0) or 0) == expected
        and parquet_meta.get("collection") == extract_report.get("collection")
    )
    if parquet_cache_valid:
        report = {
            "records": parquet_meta["records"],
            "columns": parquet_meta.get("columns", []),
            "parquet_path": str(all_paths["parquet"]),
            "parquet_sha256": parquet_meta.get("parquet_sha256"),
            "cached": True,
        }
        _write_pipeline_progress(
            status="running",
            section="parquet",
            percent=PIPELINE_PROGRESS_STEPS["parquet"],
            message="Parquet existente validado y reutilizado.",
            detail=report,
        )
        _write_state({"parquet_report": report})
        return report
    _write_pipeline_progress(
        status="running",
        section="parquet",
        percent=35,
        message="Convirtiendo JSONL a Parquet.",
        detail={"jsonl_path": str(all_paths["extract_jsonl"])},
    )
    frames = []
    try:
        for chunk in pd.read_json(all_paths["extract_jsonl"], lines=True, dtype=False, chunksize=50000):
            frames.append(chunk)
    except ValueError as exc:
        raise ValueError(
            "JSONL GA03 inválido. Vuelva a ejecutar el pipeline para regenerar "
            f"{all_paths['extract_jsonl']} desde PocketBase."
        ) from exc
    if not frames:
        raise ValueError(f"JSONL GA03 vacío: {all_paths['extract_jsonl']}")
    dataframe = pd.concat(frames, ignore_index=True)
    dataframe.to_parquet(all_paths["parquet"], index=False, compression="snappy")
    parquet_sha256 = _file_sha256(all_paths["parquet"])
    report = {
        "records": len(dataframe),
        "columns": list(dataframe.columns),
        "parquet_path": str(all_paths["parquet"]),
        "parquet_sha256": parquet_sha256,
        "cached": False,
    }
    if len(dataframe) != expected:
        raise ValueError(f"Parquet GA03 debe tener {expected} filas, actual={len(dataframe)}")
    _write_json_file(
        all_paths["parquet_meta"],
        {
            "records": len(dataframe),
            "columns": list(dataframe.columns),
            "parquet_path": str(all_paths["parquet"]),
            "parquet_sha256": parquet_sha256,
            "jsonl_sha256": extract_report.get("jsonl_sha256"),
            "collection": extract_report.get("collection"),
            "expected_records": expected,
            "created_at": utc_now_iso(),
        },
    )
    _write_pipeline_progress(
        status="running",
        section="parquet",
        percent=PIPELINE_PROGRESS_STEPS["parquet"],
        message="Parquet generado.",
        detail={"records": len(dataframe), "parquet_path": str(all_paths["parquet"])},
    )
    _write_state({"parquet_report": report})
    return report


def validate_parquet_schema_03() -> dict[str, Any]:
    all_paths = paths()
    dataframe = pd.read_parquet(all_paths["parquet"])
    missing = [column for column in REQUIRED_FACT_COLUMNS if column not in dataframe.columns]
    if missing:
        raise ValueError(f"Parquet GA03 sin columnas requeridas: {missing}")
    expected = int(_read_state()["expected_records"])
    if len(dataframe) != expected:
        raise ValueError(f"Parquet GA03 esperado={expected}, actual={len(dataframe)}")
    report = {"valid": True, "records": len(dataframe), "columns": list(dataframe.columns)}
    _write_state({"schema_report": report})
    return report


def transform_dimensions_03() -> dict[str, int]:
    all_paths = paths()
    state = _read_state()
    db = get_database()
    dimensions_ready, existing_counts = _existing_dimensions_ready(db)
    if _reuse_existing_dimensions_enabled() and dimensions_ready:
        message = "Dimensiones existentes detectadas; transformación de dimensiones omitida."
        _write_pipeline_progress(
            status="running",
            section="transform",
            percent=58,
            message=message,
            detail={"skipped": True, "dimension_counts": existing_counts},
        )
        _write_state(
            {
                "dimension_counts": existing_counts,
                "dimension_transform_skipped": True,
                "dimension_skip_reason": message,
            }
        )
        return existing_counts
    dataframe = pd.read_parquet(all_paths["parquet"])
    _, _, valid_fact_frame = transform_fact_hotel_reservations(dataframe, state["execution_id"], state["loaded_at"])
    dimensions = build_ta02_dimensions(valid_fact_frame, state["loaded_at"])
    counts = {}
    total_dimensions = max(len(DIMENSION_KEY_FIELDS), 1)
    for collection_name, documents in dimensions.items():
        counts[collection_name] = _write_jsonl(all_paths["dimension_dir"] / f"{collection_name}.jsonl", documents)
        progress = 50 + (len(counts) / total_dimensions) * 8
        _write_pipeline_progress(
            status="running",
            section="transform",
            percent=progress,
            message="Transformando dimensiones.",
            detail={"dimension": collection_name, "count": counts[collection_name], "processed_dimensions": len(counts)},
        )
    _write_state({"dimension_counts": counts})
    return counts


def transform_fact_reservations_03() -> dict[str, int]:
    all_paths = paths()
    state = _read_state()
    expected = int(state["expected_records"])
    parquet_report = state.get("parquet_report", {})
    fact_meta = _read_json_file(all_paths["fact_meta"])
    fact_cache_valid = (
        all_paths["fact_jsonl"].exists()
        and all_paths["rejected_jsonl"].exists()
        and fact_meta.get("parquet_sha256") == parquet_report.get("parquet_sha256")
        and int(fact_meta.get("fact_hotel_reservations", -1)) == expected
        and int(fact_meta.get("rejected_records", -1)) == 0
        and int(fact_meta.get("fact_jsonl_bytes", -1)) == all_paths["fact_jsonl"].stat().st_size
        and int(fact_meta.get("rejected_jsonl_bytes", -1)) == all_paths["rejected_jsonl"].stat().st_size
    )
    if fact_cache_valid:
        report = {
            "fact_hotel_reservations": expected,
            "rejected_records": 0,
            "cached": True,
        }
        _write_pipeline_progress(
            status="running",
            section="transform",
            percent=PIPELINE_PROGRESS_STEPS["transform"],
            message="Hecho transformado existente validado y reutilizado.",
            detail=report,
        )
        _write_state({"fact_transform_counts": report})
        return report
    _write_pipeline_progress(
        status="running",
        section="transform",
        percent=60,
        message="Transformando hecho fact_hotel_reservations.",
        detail={"fact_collection": "fact_hotel_reservations"},
    )
    dataframe = pd.read_parquet(all_paths["parquet"])
    facts, rejected, _ = transform_fact_hotel_reservations(dataframe, state["execution_id"], state["loaded_at"])
    for document in facts:
        document["phase"] = PHASE
    for document in rejected:
        document["phase"] = PHASE
    fact_count = _write_jsonl(all_paths["fact_jsonl"], facts)
    rejected_count = _write_jsonl(all_paths["rejected_jsonl"], rejected)
    if fact_count != expected or rejected_count != 0:
        raise ValueError(f"Transformacion GA03 invalida: hechos={fact_count}, rechazados={rejected_count}, esperado={expected}")
    report = {"fact_hotel_reservations": fact_count, "rejected_records": rejected_count, "cached": False}
    _write_json_file(
        all_paths["fact_meta"],
        {
            "fact_hotel_reservations": fact_count,
            "rejected_records": rejected_count,
            "fact_jsonl_bytes": all_paths["fact_jsonl"].stat().st_size,
            "rejected_jsonl_bytes": all_paths["rejected_jsonl"].stat().st_size,
            "fact_jsonl_sha256": _file_sha256(all_paths["fact_jsonl"]),
            "rejected_jsonl_sha256": _file_sha256(all_paths["rejected_jsonl"]),
            "parquet_sha256": parquet_report.get("parquet_sha256"),
            "collection": state.get("extract_report", {}).get("collection"),
            "expected_records": expected,
            "created_at": utc_now_iso(),
        },
    )
    _write_pipeline_progress(
        status="running",
        section="transform",
        percent=PIPELINE_PROGRESS_STEPS["transform"],
        message="Transformación de hecho completada.",
        detail=report,
    )
    _write_state({"fact_transform_counts": report})
    return report


def load_dimensions_to_mongodb_03() -> dict[str, int]:
    all_paths = paths()
    state = _read_state()
    if state.get("dimension_transform_skipped"):
        counts = state.get("dimension_counts") or _dimension_collection_counts(get_database())
        message = "Carga de dimensiones omitida; colecciones existentes reutilizadas."
        _write_pipeline_progress(
            status="running",
            section="load_mongodb",
            percent=72,
            message=message,
            detail={"skipped": True, "dimension_counts": counts},
        )
        _write_state(
            {
                "dimension_load_counts": counts,
                "dimension_load_skipped": True,
                "dimension_load_skip_reason": message,
            }
        )
        return counts
    dimensions: dict[str, list[dict[str, Any]]] = {}
    for collection_name in DIMENSION_KEY_FIELDS:
        dimensions[collection_name] = list(_iter_jsonl(all_paths["dimension_dir"] / f"{collection_name}.jsonl") or [])
    counts = upsert_dimensions(get_database(), dimensions)
    _write_pipeline_progress(
        status="running",
        section="load_mongodb",
        percent=72,
        message="Dimensiones cargadas en MongoDB.",
        detail=counts,
    )
    _write_state({"dimension_load_counts": counts})
    return counts


def load_fact_to_mongodb_03() -> dict[str, int]:
    all_paths = paths()
    db = get_database()
    expected = int(_read_state()["expected_records"])
    full_reload = os.getenv("GA03_FULL_RELOAD_FACTS", "true").lower() == "true"
    previous_count = db.fact_hotel_reservations.count_documents({})
    expected_new_count = _count_jsonl(all_paths["fact_jsonl"])
    if expected_new_count != expected:
        raise ValueError(f"JSONL hecho GA03 esperado={expected}, actual={expected_new_count}")
    deleted = 0
    print(f"GA03 conteo anterior fact_hotel_reservations: {previous_count}")
    if full_reload:
        deleted = db.fact_hotel_reservations.delete_many({}).deleted_count
        _write_pipeline_progress(
            status="running",
            section="load_mongodb",
            percent=76,
            message="Hecho anterior limpiado para full reload.",
            detail={"deleted": deleted, "previous_count": previous_count},
        )
        fact_count = _insert_fact_jsonl(db, all_paths["fact_jsonl"])
    else:
        db.fact_hotel_reservations.create_index("source_record_id")
        fact_count = _upsert_fact_jsonl_by_source_record_id(db, all_paths["fact_jsonl"])
    rejected_count = _count_jsonl(all_paths["rejected_jsonl"])
    if rejected_count:
        rejected_batch = []
        for rejected in _iter_jsonl(all_paths["rejected_jsonl"]):
            rejected["phase"] = PHASE
            rejected_batch.append(rejected)
        if rejected_batch:
            db.rejected_records.insert_many(rejected_batch, ordered=False)
    final_count = db.fact_hotel_reservations.count_documents({})
    if final_count != expected:
        raise RuntimeError(f"GA03 conteo final inesperado: esperado={expected}, actual={final_count}")
    counts = {
        "previous_fact_hotel_reservations": previous_count,
        "deleted_facts_before_load": deleted,
        "fact_hotel_reservations": fact_count,
        "expected_fact_hotel_reservations": expected_new_count,
        "final_fact_hotel_reservations": final_count,
        "rejected_records": rejected_count,
    }
    _write_pipeline_progress(
        status="running",
        section="load_mongodb",
        percent=PIPELINE_PROGRESS_STEPS["load_mongodb"],
        message="Carga de hecho en MongoDB completada.",
        detail=counts,
    )
    _write_state({"fact_load_counts": counts})
    return counts


def create_indexes_03() -> dict[str, list[str]]:
    result = create_ta02_indexes(get_database())
    _write_pipeline_progress(
        status="running",
        section="reports",
        percent=92,
        message="Índices MongoDB creados.",
        detail=result,
    )
    _write_state({"indexes": result})
    return result


def run_quality_checks_03() -> dict[str, Any]:
    all_paths = paths()
    state = _read_state()
    schema = state.get("schema_report", {})
    fact_counts = state.get("fact_transform_counts", {})
    dimension_counts = state.get("dimension_counts", {})
    report = build_quality_report(
        execution_id=state["execution_id"],
        source_path=str(all_paths["parquet"]),
        source_rows=int(schema.get("records", 0) or 0),
        valid_fact_records=int(fact_counts.get("fact_hotel_reservations", 0) or 0),
        rejected_records=int(fact_counts.get("rejected_records", 0) or 0),
        dimensions=dimension_counts,
        schema=schema,
        extract=state.get("extract_report", {}),
        parquet=state.get("parquet_report", {}),
    )
    write_json_report(all_paths["quality_report"], report)
    _write_pipeline_progress(
        status="running",
        section="reports",
        percent=96,
        message="Reporte de calidad generado.",
        detail={"valid_fact_records": report.get("valid_fact_records"), "rejected_records": report.get("rejected_records")},
    )
    _write_state({"quality_report": report})
    return report


def save_execution_report_03() -> dict[str, Any]:
    all_paths = paths()
    state = _read_state()
    db = get_database()
    completed_at = utc_now_iso()
    started = datetime.fromisoformat(state["started_at"])
    completed = datetime.fromisoformat(completed_at)
    collections = [*DIMENSION_KEY_FIELDS.keys(), "fact_hotel_reservations", "rejected_records", "etl_executions", "data_quality_reports"]
    final_counts = collection_counts(db, collections)
    execution_report = build_execution_report(
        execution_id=state["execution_id"],
        started_at=state["started_at"],
        completed_at=completed_at,
        duration_seconds=(completed - started).total_seconds(),
        database=state["database"],
        source_path=str(all_paths["parquet"]),
        loaded_collections={**state.get("dimension_load_counts", {}), **state.get("fact_load_counts", {})},
        final_counts=final_counts,
    )
    quality_report = state.get("quality_report")
    if quality_report is None:
        raise RuntimeError("No existe reporte de calidad GA03 en estado")
    insert_ga03_reports(db, quality_report, execution_report)
    write_json_report(all_paths["execution_report"], execution_report)
    _write_pipeline_progress(
        status="completed",
        section="reports",
        percent=PIPELINE_PROGRESS_STEPS["reports"],
        message="Pipeline GA03 completado.",
        detail={"execution_id": state["execution_id"], "duration_seconds": execution_report.get("duration_seconds")},
    )
    _write_state({"execution_report": execution_report})
    return {"status": "success", "execution_id": state["execution_id"], "report_saved": True}


def run_pipeline_03() -> dict[str, Any]:
    global PIPELINE_STARTED_MONO
    PIPELINE_STARTED_MONO = time.perf_counter()
    try:
        validate_environment_03()
        extract_from_pocketbase_03()
        save_extract_jsonl_03()
        convert_to_parquet_03()
        validate_parquet_schema_03()
        transform_dimensions_03()
        transform_fact_reservations_03()
        load_dimensions_to_mongodb_03()
        load_fact_to_mongodb_03()
        create_indexes_03()
        run_quality_checks_03()
        return save_execution_report_03()
    except Exception as exc:
        _write_pipeline_progress(
            status="failed",
            section="error",
            percent=0,
            message=str(exc),
            detail={"error_type": type(exc).__name__},
        )
        raise
