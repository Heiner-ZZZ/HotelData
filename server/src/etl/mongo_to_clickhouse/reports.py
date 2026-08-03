"""Reportes de ejecución y calidad del pipeline mongo_to_clickhouse."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from config.settings import get_settings
from src.etl.mongo_to_clickhouse._common import elapsed_ms, write_json_file
from src.etl.mongo_to_clickhouse.config import ALL_TABLES, paths


def run_quality_checks(load_counts: dict[str, int]) -> dict[str, Any]:
    """Valida que cada tabla esperada haya tenido intención de carga.

    Una tabla con ``-1`` significa "sin esquema definido" (no se intentó cargar).
    Con ``0`` filas puede ser legítimo (sin datos nuevos ese día), por lo que no
    se marca como error — pero se reporta para visibilidad.
    """
    checks: dict[str, Any] = {}
    for table_name in ALL_TABLES:
        count = load_counts.get(table_name, -1)
        if count == -1:
            checks[table_name] = {"loaded": 0, "state": "skipped"}
        else:
            checks[table_name] = {"loaded": count, "state": "ok" if count > 0 else "empty"}
    failed = [name for name, info in checks.items() if info["state"] == "skipped"]
    return {
        "ok": not failed,
        "tables": checks,
        "failed_tables": failed,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def save_execution_report(
    started_at: float,
    metrics: dict[str, Any],
    quality: dict[str, Any] | None = None,
    *,
    started_at_iso: str | None = None,
) -> dict[str, Any]:
    """Escribe el reporte de ejecución en ``config.paths()['execution_report']``.

    ``started_at`` es un contador monotónico usado únicamente para medir duración;
    ``started_at_iso`` es la fecha/hora de pared que se muestra en la UI. Separar
    ambos evita convertir ``time.perf_counter()`` en una fecha Unix de 1970.
    """
    settings = get_settings()
    report = {
        "pipeline": "mongo_to_clickhouse",
        "started_at": started_at_iso or "",
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_ms": elapsed_ms(started_at),
        "clickhouse_database": settings.clickhouse_database,
        "metrics": metrics,
        "quality": quality or {},
        "status": "success" if (quality or {}).get("ok", True) else "failed",
    }
    write_json_file(paths()["execution_report"], report)
    return report
