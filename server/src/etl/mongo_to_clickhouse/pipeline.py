"""Orquestación programática del pipeline MongoDB → ClickHouse.

Flujo: validate_config → extract_mongo → transform → create_tables →
load_clickhouse → quality_report → execution_report. Actualiza el archivo de
progreso (vía ``progress_service``/JSON) y respeta un stop flag entre etapas.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from config.settings import get_settings
from src.etl.mongo_to_clickhouse._common import read_json_file, write_json_file
from src.etl.mongo_to_clickhouse.config import (
    ALL_TABLES,
    PIPELINE_PROGRESS_LABELS,
    PIPELINE_PROGRESS_ORDER,
    PIPELINE_PROGRESS_STEPS,
    paths,
)
from src.etl.mongo_to_clickhouse.extract import extract_all
from src.etl.mongo_to_clickhouse.load import clickhouse_client, create_tables, load_all
from src.etl.mongo_to_clickhouse.reports import run_quality_checks, save_execution_report
from src.etl.mongo_to_clickhouse.transform import TABLE_COLUMNS, transform_rows


def _progress(
    percent: int,
    section: str,
    message: str,
    *,
    status: str = "running",
    detail: dict[str, Any] | None = None,
) -> None:
    progress_path = paths()["progress"]
    previous = read_json_file(progress_path)
    previous_sections = previous.get("sections", {})
    is_new_run = section == "validate_config" and percent == 0 and status == "running"
    sections = {
        key: {
            "label": PIPELINE_PROGRESS_LABELS[key],
            "complete": False if is_new_run else (
                previous_sections.get(key, {}).get("complete", False)
                or (percent >= PIPELINE_PROGRESS_STEPS[key] and status == "completed")
            ),
        }
        for key in PIPELINE_PROGRESS_ORDER
    }
    # Al alcanzar una etapa, todas las etapas anteriores ya terminaron.
    current_index = PIPELINE_PROGRESS_ORDER.index(section) if section in PIPELINE_PROGRESS_ORDER else -1
    if status == "running" and current_index >= 0:
        for key in PIPELINE_PROGRESS_ORDER[:current_index]:
            sections[key]["complete"] = True
    if status == "completed":
        for key in PIPELINE_PROGRESS_ORDER:
            sections[key]["complete"] = True

    write_json_file(
        progress_path,
        {
            **previous,
            "status": status,
            "percent": percent,
            "section": section,
            "message": message,
            "detail": detail or {},
            "sections": sections,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )


def _stop_requested() -> bool:
    """True si existe el flag de detención (se consume al terminar la corrida).

    El flag es efímero por corrida: ``start_pipeline`` lo borra antes de lanzar
    y el ``finally`` de la corrida lo elimina, de modo que una detención nunca
    bloquea ejecuciones futuras.
    """
    settings = get_settings()
    flag = settings.reports_dir / "m2c_stop.flag"
    return flag.exists()


def _clear_stop_flag() -> None:
    settings = get_settings()
    flag = settings.reports_dir / "m2c_stop.flag"
    try:
        flag.unlink(missing_ok=True)
    except OSError:
        pass


def validate_config() -> dict[str, Any]:
    """Valida prerrequisitos: MongoDB alcanzable, ClickHouse alcanzable, tablas definidas."""
    settings = get_settings()
    errors: list[str] = []
    from pymongo import MongoClient

    mongo = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=5000)
    try:
        mongo.admin.command("ping")
    except Exception as exc:
        errors.append(f"MongoDB no disponible: {exc}")
    finally:
        mongo.close()

    try:
        client = clickhouse_client(settings)
        client.command("SELECT 1")
        client.close()
    except Exception as exc:
        errors.append(f"ClickHouse no disponible: {exc}")

    missing = [t for t in ALL_TABLES if t not in TABLE_COLUMNS]
    if missing:
        errors.append(f"Tablas sin esquema definido: {missing}")

    from src.etl.mongo_to_clickhouse.load import LABEL_COLUMNS, TABLES_DDL
    for table_name, labels in LABEL_COLUMNS.items():
        if table_name not in ALL_TABLES:
            continue
        columns_sql = TABLES_DDL[table_name][0]
        for label_name, _ in labels:
            if label_name not in TABLE_COLUMNS[table_name] or label_name not in columns_sql:
                errors.append(f"Label sin contrato completo: {table_name}.{label_name}")

    return {"ok": not errors, "errors": errors, "clickhouse_database": settings.clickhouse_database}


# ─── Etapas individuales (usadas por el DAG, sin XCom) ───────────────

def _write_progress(
    percent: int,
    section: str,
    message: str,
    *,
    status: str = "running",
    detail: dict[str, Any] | None = None,
) -> None:
    _progress(percent, section, message, status=status, detail=detail)


def stage_validate_config() -> dict[str, Any]:
    """Valida entorno (Mongo + ClickHouse) y escribe el resultado en staging."""
    started_at = time.perf_counter()
    started_at_iso = datetime.now(timezone.utc).isoformat()
    _write_progress(0, "validate_config", "Validating configuration…")
    result = validate_config()
    if not result["ok"]:
        _write_progress(0, "validate_config", "Configuration validation failed: " + "; ".join(result["errors"]), status="failed")
        raise RuntimeError("Validación fallida: " + "; ".join(result["errors"]))
    write_json_file(
        paths()["state"],
        {"validate_config": {**result, "started_at": started_at, "started_at_iso": started_at_iso}},
    )
    _write_progress(PIPELINE_PROGRESS_STEPS["validate_config"], "extract_mongo", "Extracting from MongoDB…")
    return result


def stage_extract_mongo() -> dict[str, Any]:
    """Extrae los KPI agregados de MongoDB y guarda el payload en staging JSON."""
    settings = get_settings()
    payload = extract_all(client=None, db_name=settings.mongo_database)
    write_json_file(paths()["extract_json"], payload)
    counts = {name: len(docs) for name, docs in payload.items()}
    _write_progress(PIPELINE_PROGRESS_STEPS["extract_mongo"], "transform", "Transforming rows…", detail={"extract_counts": counts})
    return {"tables": counts}


def stage_transform() -> dict[str, Any]:
    """Lee el extract JSON, transforma cada tabla y guarda las filas en staging."""
    from src.etl.mongo_to_clickhouse._common import read_json_file

    payload = read_json_file(paths()["extract_json"])
    transformed = {table: transform_rows(table, docs) for table, docs in payload.items()}
    write_json_file(paths()["transformed_json"], transformed)
    counts = {name: len(rows) for name, rows in transformed.items()}
    _write_progress(PIPELINE_PROGRESS_STEPS["transform"], "create_tables", "Creating ClickHouse tables…")
    return {"tables": counts}


def stage_create_tables() -> dict[str, Any]:
    """Crea las tablas en ClickHouse (idempotente)."""
    settings = get_settings()
    client = clickhouse_client(settings)
    try:
        result = create_tables(client, settings.clickhouse_database, ALL_TABLES)
    finally:
        client.close()
    _write_progress(PIPELINE_PROGRESS_STEPS["create_tables"], "load_clickhouse", "Loading data into ClickHouse…")
    return result


def stage_load_clickhouse() -> dict[str, int]:
    """Lee las filas transformadas y las inserta (upsert idempotente)."""
    from src.etl.mongo_to_clickhouse._common import read_json_file

    settings = get_settings()
    transformed = read_json_file(paths()["transformed_json"])
    client = clickhouse_client(settings)
    try:
        counts = load_all(client, settings.clickhouse_database, transformed)
    finally:
        client.close()
    write_json_file(paths()["load_counts_json"], counts)
    _write_progress(
        PIPELINE_PROGRESS_STEPS["load_clickhouse"],
        "quality_report",
        "Running quality checks…",
        detail={"load_counts": counts},
    )
    return counts


def stage_quality_report() -> dict[str, Any]:
    """Ejecuta checks de calidad sobre los conteos de carga guardados."""
    from src.etl.mongo_to_clickhouse._common import read_json_file

    counts = read_json_file(paths()["load_counts_json"])
    quality = run_quality_checks(counts)
    write_json_file(paths()["quality_report"], quality)
    _write_progress(PIPELINE_PROGRESS_STEPS["quality_report"], "execution_report", "Generating execution report…")
    return quality


def stage_execution_report() -> dict[str, Any]:
    """Consolida métricas de staging y escribe el reporte final de ejecución."""
    from src.etl.mongo_to_clickhouse._common import read_json_file

    counts = read_json_file(paths()["load_counts_json"])
    quality = read_json_file(paths()["quality_report"])
    state = read_json_file(paths()["state"])
    started_raw = (state.get("validate_config") or {}).get("started_at")
    started_at = float(started_raw) if started_raw else time.perf_counter()
    started_at_iso = (state.get("validate_config") or {}).get("started_at_iso")
    report = save_execution_report(
        started_at,
        {"rows_by_table": counts},
        quality,
        started_at_iso=started_at_iso,
    )
    status = "completed" if report.get("status") == "success" else "failed"
    _write_progress(
        PIPELINE_PROGRESS_STEPS["execution_report"],
        "execution_report",
        "Pipeline completed." if status == "completed" else "Pipeline failed.",
        status=status,
        detail={"rows_by_table": counts},
    )
    return report


def run_pipeline(incremental: bool = True) -> dict[str, Any]:
    """Ejecuta una recomposición táctica de agregados desde Mongo.

    ``incremental`` se conserva únicamente por compatibilidad con callers
    antiguos; el pipeline M2C no interpreta documentos nuevos frente a viejos.
    Cada ejecución recalcula los agregados definidos y los publica en
    ClickHouse mediante las claves naturales de ``ReplacingMergeTree``.
    """
    started_at = time.perf_counter()
    started_at_iso = datetime.now(timezone.utc).isoformat()
    settings = get_settings()
    _progress(0, "validate_config", "Validating configuration…")

    _clear_stop_flag()  # una corrida nueva parte limpia (consumir stop previo)
    config_result = validate_config()
    if not config_result["ok"]:
        _progress(0, "validate_config", "Configuration validation failed: " + "; ".join(config_result["errors"]), status="failed")
        return {"ok": False, "errors": config_result["errors"]}
    _progress(PIPELINE_PROGRESS_STEPS["validate_config"], "extract_mongo", "Extracting from MongoDB…")

    if _stop_requested():
        _progress(0, "extract_mongo", "Stop requested.", status="stopped")
        return {"ok": False, "errors": ["Stop requested."]}

    # 1. Extract (agregaciones en origen)
    payload = extract_all(client=None, db_name=settings.mongo_database)
    _progress(PIPELINE_PROGRESS_STEPS["extract_mongo"], "transform", "Transforming rows…")

    if _stop_requested():
        _progress(0, "transform", "Stop requested.", status="stopped")
        return {"ok": False, "errors": ["Stop requested."]}

    # 2. Transform (por tabla)
    transformed = {table: transform_rows(table, docs) for table, docs in payload.items()}
    _progress(PIPELINE_PROGRESS_STEPS["transform"], "create_tables", "Creating ClickHouse tables…")

    # 3. Create tables
    client = clickhouse_client(settings)
    try:
        create_tables(client, settings.clickhouse_database, ALL_TABLES)
        _progress(PIPELINE_PROGRESS_STEPS["create_tables"], "load_clickhouse", "Loading data into ClickHouse…")

        if _stop_requested():
            _progress(0, "load_clickhouse", "Stop requested.", status="stopped")
            return {"ok": False, "errors": ["Stop requested."]}

        # 4. Load (upsert idempotente)
        counts = load_all(client, settings.clickhouse_database, transformed)
        _progress(
            PIPELINE_PROGRESS_STEPS["load_clickhouse"],
            "quality_report",
            "Running quality checks…",
            detail={"load_counts": counts},
        )

        # 5. Quality
        quality = run_quality_checks(counts)
        _progress(PIPELINE_PROGRESS_STEPS["quality_report"], "execution_report", "Generating execution report…")

        # 6. Report
        metrics = {
            "rows_by_table": counts,
            # El M2C recompone agregados desde Mongo; no es un incremental de documentos.
            "refresh_mode": "aggregate_refresh",
            "incremental": False,
        }
        save_execution_report(started_at, metrics, quality, started_at_iso=started_at_iso)
        final_status = "completed" if quality["ok"] else "failed"
        _progress(
            PIPELINE_PROGRESS_STEPS["execution_report"],
            "execution_report",
            "Pipeline completed." if final_status == "completed" else "Pipeline completed with empty tables.",
            status=final_status,
            detail={"rows_by_table": counts},
        )
        return {
            "ok": quality["ok"],
            "rows_by_table": counts,
            "elapsed_ms": int((time.perf_counter() - started_at) * 1000),
            "quality": quality,
        }
    except Exception as exc:
        _progress(0, "execution_report", f"Pipeline failed: {exc}", status="failed")
        return {"ok": False, "errors": [str(exc)]}
    finally:
        _clear_stop_flag()  # el stop se consume al terminar la corrida
        client.close()
