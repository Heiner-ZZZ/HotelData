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
    DEFAULT_REFRESH_MODE,
    ETL_PIPELINE_CONFIG_COLLECTION,
    PIPELINE,
    PIPELINE_PROGRESS_LABELS,
    PIPELINE_PROGRESS_ORDER,
    PIPELINE_PROGRESS_STEPS,
    REFRESH_MODES,
    paths,
)
from src.etl.mongo_to_clickhouse.extract import extract_all
from src.etl.mongo_to_clickhouse.load import clickhouse_client, create_tables, load_all
from src.etl.mongo_to_clickhouse.parquet_export import (
    export_crudo,
    export_procesado,
    export_terminado,
    record_dato_section,
    reset_dato_export,
)
from src.etl.mongo_to_clickhouse.reports import (
    run_date_health_checks,
    run_quality_checks,
    save_execution_report,
)
from src.etl.mongo_to_clickhouse.transform import (
    TABLE_COLUMNS,
    transform_rows_with_stats,
)


def resolve_refresh_mode() -> str:
    """Lee ``refresh_mode`` de ``etl_pipeline_config`` (fallback ``full``).

    Es la misma colección que guarda el horario del DAG: la UI escribe aquí y
    la automatización horaria (y el botón de la UI) leen el mismo documento en
    cada corrida. Un valor inválido o la ausencia de documento caen en
    ``DEFAULT_REFRESH_MODE`` sin romper el run.
    """
    try:
        settings = get_settings()
        from pymongo import MongoClient

        client = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=3000)
        try:
            doc = client[settings.mongo_database][ETL_PIPELINE_CONFIG_COLLECTION].find_one(
                {"pipeline": PIPELINE}
            )
            mode = (doc or {}).get("refresh_mode")
            if mode in REFRESH_MODES:
                return mode
        finally:
            client.close()
    except Exception:  # pragma: no cover - fallback silencioso
        pass
    return DEFAULT_REFRESH_MODE


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


def stage_validate_config(run_date: str | None = None) -> dict[str, Any]:
    """Valida entorno (Mongo + ClickHouse) y escribe el resultado en staging."""
    started_at = time.perf_counter()
    started_at_iso = datetime.now(timezone.utc).isoformat()
    # Corrida nueva: el registro de parquet arranca vacío para no mezclar
    # secciones de corridas anteriores si este run falla a mitad.
    reset_dato_export(run_date)
    _write_progress(0, "validate_config", "Validating configuration…")
    result = validate_config()
    if not result["ok"]:
        _write_progress(0, "validate_config", "Configuration validation failed: " + "; ".join(result["errors"]), status="failed")
        raise RuntimeError("Validación fallida: " + "; ".join(result["errors"]))
    # El modo de refresco lo elige la UI (etl_pipeline_config) y el DAG lo
    # lee en cada corrida; se persiste en state para que las etapas siguientes
    # (load) lo usen sin re-consultar Mongo.
    refresh_mode = resolve_refresh_mode()
    write_json_file(
        paths()["state"],
        {
            "validate_config": {**result, "started_at": started_at, "started_at_iso": started_at_iso},
            "refresh_mode": refresh_mode,
        },
    )
    _write_progress(
        PIPELINE_PROGRESS_STEPS["validate_config"],
        "extract_mongo",
        "Extracting from MongoDB…",
        detail={"refresh_mode": refresh_mode},
    )
    _write_progress(PIPELINE_PROGRESS_STEPS["validate_config"], "extract_mongo", "Extracting from MongoDB…")
    return result


def stage_extract_mongo(run_date: str | None = None) -> dict[str, Any]:
    """Extrae los KPI agregados de MongoDB, guarda el payload y exporta Crudo."""
    settings = get_settings()
    payload = extract_all(client=None, db_name=settings.mongo_database)
    write_json_file(paths()["extract_json"], payload)
    counts = {name: len(docs) for name, docs in payload.items()}
    crudo_counts = export_crudo(payload, run_date)
    record_dato_section("Crudo", crudo_counts, run_date)
    _write_progress(PIPELINE_PROGRESS_STEPS["extract_mongo"], "transform", "Transforming rows…", detail={"extract_counts": counts, "parquet_crudo": crudo_counts})
    return {"tables": counts, "parquet_crudo": crudo_counts}


def stage_transform(run_date: str | None = None) -> dict[str, Any]:
    """Lee el extract JSON, transforma cada tabla y exporta Procesado.

    Las filas sin fecha válida se descartan (nunca un 1970-01-01 en
    ClickHouse) y su conteo queda en ``m2c_discarded.json`` para el reporte
    de calidad.
    """
    from src.etl.mongo_to_clickhouse._common import read_json_file

    payload = read_json_file(paths()["extract_json"])
    transformed: dict[str, list] = {}
    discarded: dict[str, int] = {}
    for table, docs in payload.items():
        rows, discarded_count = transform_rows_with_stats(table, docs)
        transformed[table] = rows
        discarded[table] = discarded_count
    write_json_file(paths()["transformed_json"], transformed)
    write_json_file(paths()["discarded_json"], discarded)
    counts = {name: len(rows) for name, rows in transformed.items()}
    procesado_counts = export_procesado(transformed, run_date)
    record_dato_section("Procesado", procesado_counts, run_date)
    _write_progress(
        PIPELINE_PROGRESS_STEPS["transform"],
        "create_tables",
        "Creating ClickHouse tables…",
        detail={"parquet_procesado": procesado_counts, "discarded_rows": discarded},
    )
    return {"tables": counts, "parquet_procesado": procesado_counts, "discarded_rows": discarded}


def stage_create_tables() -> dict[str, Any]:
    """Crea las tablas en ClickHouse (idempotente) con TTL de retención."""
    settings = get_settings()
    client = clickhouse_client(settings)
    try:
        result = create_tables(
            client,
            settings.clickhouse_database,
            ALL_TABLES,
            ttl_months=settings.kpi_ttl_months,
        )
    finally:
        client.close()
    _write_progress(
        PIPELINE_PROGRESS_STEPS["create_tables"],
        "load_clickhouse",
        "Loading data into ClickHouse…",
        detail={"ttl_months": settings.kpi_ttl_months},
    )
    return result


def stage_load_clickhouse(run_date: str | None = None) -> dict[str, int]:
    """Lee las filas transformadas, las inserta y exporta Terminado."""
    from src.etl.mongo_to_clickhouse._common import read_json_file

    settings = get_settings()
    transformed = read_json_file(paths()["transformed_json"])
    state = read_json_file(paths()["state"])
    refresh_mode = state.get("refresh_mode") or resolve_refresh_mode()
    client = clickhouse_client(settings)
    try:
        counts = load_all(client, settings.clickhouse_database, transformed, refresh_mode=refresh_mode)
    finally:
        client.close()
    write_json_file(paths()["load_counts_json"], counts)
    # Terminado solo se materializa tras un load exitoso: es el producto final.
    terminado_counts = export_terminado(transformed, run_date)
    record_dato_section("Terminado", terminado_counts, run_date)
    _write_progress(
        PIPELINE_PROGRESS_STEPS["load_clickhouse"],
        "quality_report",
        "Running quality checks…",
        detail={"load_counts": counts, "parquet_terminado": terminado_counts},
    )
    return counts


def stage_quality_report() -> dict[str, Any]:
    """Ejecuta checks de calidad sobre los conteos, descartadas y fechas."""
    from src.etl.mongo_to_clickhouse._common import read_json_file

    counts = read_json_file(paths()["load_counts_json"])
    discarded = read_json_file(paths()["discarded_json"])
    settings = get_settings()
    client = clickhouse_client(settings)
    try:
        date_checks = run_date_health_checks(
            client, settings.clickhouse_database, ALL_TABLES
        )
    finally:
        client.close()
    quality = run_quality_checks(counts, discarded_by_table=discarded)
    quality["date_checks"] = date_checks
    write_json_file(paths()["quality_report"], quality)
    _write_progress(
        PIPELINE_PROGRESS_STEPS["quality_report"],
        "execution_report",
        "Generating execution report…",
        detail={
            "date_checks_ok": date_checks.get("ok"),
            "warned_tables": date_checks.get("warned_tables", []),
        },
    )
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


def run_pipeline(incremental: bool = True, refresh_mode: str | None = None) -> dict[str, Any]:
    """Ejecuta una recomposición táctica de agregados desde Mongo.

    ``incremental`` se conserva únicamente por compatibilidad con callers
    antiguos (ver ``refresh_mode``). ``refresh_mode`` admite ``"full"``
    (barrido: TRUNCATE + INSERT) o ``"incremental"`` (INSERT + dedup de
    ReplacingMergeTree, sin borrar historial); si es ``None`` se lee el valor
    persistido en ``etl_pipeline_config`` (el mismo que usa el DAG horario).
    """
    started_at = time.perf_counter()
    started_at_iso = datetime.now(timezone.utc).isoformat()
    settings = get_settings()
    _progress(0, "validate_config", "Validating configuration…")

    _clear_stop_flag()  # una corrida nueva parte limpia (consumir stop previo)
    reset_dato_export()  # registro de parquet de la corrida nueva, sin mezclas
    config_result = validate_config()
    if not config_result["ok"]:
        _progress(0, "validate_config", "Configuration validation failed: " + "; ".join(config_result["errors"]), status="failed")
        return {"ok": False, "errors": config_result["errors"]}
    if refresh_mode is None:
        refresh_mode = resolve_refresh_mode()
    if refresh_mode not in REFRESH_MODES:
        refresh_mode = DEFAULT_REFRESH_MODE
    _progress(
        PIPELINE_PROGRESS_STEPS["validate_config"],
        "extract_mongo",
        "Extracting from MongoDB…",
        detail={"refresh_mode": refresh_mode},
    )

    if _stop_requested():
        _progress(0, "extract_mongo", "Stop requested.", status="stopped")
        return {"ok": False, "errors": ["Stop requested."]}

    # 1. Extract (agregaciones en origen) + sección Crudo del directorio Dato.
    payload = extract_all(client=None, db_name=settings.mongo_database)
    crudo_counts = export_crudo(payload)
    record_dato_section("Crudo", crudo_counts)
    _progress(PIPELINE_PROGRESS_STEPS["extract_mongo"], "transform", "Transforming rows…")

    if _stop_requested():
        _progress(0, "transform", "Stop requested.", status="stopped")
        return {"ok": False, "errors": ["Stop requested."]}

    # 2. Transform (por tabla) + sección Procesado. Las filas sin fecha
    #    válida se descartan (nunca un 1970-01-01 en ClickHouse) y se cuentan
    #    para el reporte de calidad.
    transformed: dict[str, list] = {}
    discarded: dict[str, int] = {}
    for table, docs in payload.items():
        rows, discarded_count = transform_rows_with_stats(table, docs)
        transformed[table] = rows
        discarded[table] = discarded_count
    write_json_file(paths()["discarded_json"], discarded)
    procesado_counts = export_procesado(transformed)
    record_dato_section("Procesado", procesado_counts)
    _progress(PIPELINE_PROGRESS_STEPS["transform"], "create_tables", "Creating ClickHouse tables…")

    # 3. Create tables (con TTL de retención configurable)
    client = clickhouse_client(settings)
    try:
        create_tables(
            client,
            settings.clickhouse_database,
            ALL_TABLES,
            ttl_months=settings.kpi_ttl_months,
        )
        _progress(
            PIPELINE_PROGRESS_STEPS["create_tables"],
            "load_clickhouse",
            "Loading data into ClickHouse…",
            detail={"ttl_months": settings.kpi_ttl_months},
        )

        if _stop_requested():
            _progress(0, "load_clickhouse", "Stop requested.", status="stopped")
            return {"ok": False, "errors": ["Stop requested."]}

        # 4. Load (upsert idempotente) + sección Terminado (producto final).
        counts = load_all(
            client,
            settings.clickhouse_database,
            transformed,
            refresh_mode=refresh_mode,
        )
        terminado_counts = export_terminado(transformed)
        record_dato_section("Terminado", terminado_counts)
        _progress(
            PIPELINE_PROGRESS_STEPS["load_clickhouse"],
            "quality_report",
            "Running quality checks…",
            detail={"load_counts": counts, "refresh_mode": refresh_mode},
        )

        # 5. Quality (incluye descartadas por fecha inválida + salud de fechas
        #    en ClickHouse: 1970-01-01 o rango vacío marcan warning).
        quality = run_quality_checks(counts, discarded_by_table=discarded)
        quality["date_checks"] = run_date_health_checks(
            client, settings.clickhouse_database, ALL_TABLES
        )
        _progress(PIPELINE_PROGRESS_STEPS["quality_report"], "execution_report", "Generating execution report…")

        # 6. Report
        metrics = {
            "rows_by_table": counts,
            # Modo efectivo de la corrida (elegido en la UI / DAG): "full" =
            # barrido con TRUNCATE, "incremental" = INSERT + dedup sin borrado.
            "refresh_mode": refresh_mode,
            "incremental": refresh_mode == "incremental",
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
