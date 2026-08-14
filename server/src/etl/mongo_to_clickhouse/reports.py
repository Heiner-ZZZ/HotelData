"""Reportes de ejecución y calidad del pipeline mongo_to_clickhouse."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from config.settings import get_settings
from src.etl.mongo_to_clickhouse._common import elapsed_ms, write_json_file
from src.etl.mongo_to_clickhouse.config import ALL_TABLES, paths


def run_quality_checks(
    load_counts: dict[str, int],
    discarded_by_table: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Valida que cada tabla esperada haya tenido intención de carga.

    Una tabla con ``-1`` significa "sin esquema definido" (no se intentó cargar).
    Con ``0`` filas puede ser legítimo (sin datos nuevos ese día), por lo que no
    se marca como error — pero se reporta para visibilidad.

    ``discarded_by_table`` suma las filas que el transform descartó por fecha
    inválida; se exponen por tabla y en el total del reporte para auditoría.
    """
    discarded_by_table = discarded_by_table or {}
    checks: dict[str, Any] = {}
    for table_name in ALL_TABLES:
        count = load_counts.get(table_name, -1)
        discarded = int(discarded_by_table.get(table_name, 0) or 0)
        if count == -1:
            checks[table_name] = {"loaded": 0, "state": "skipped", "discarded_rows": discarded}
        else:
            checks[table_name] = {
                "loaded": count,
                "state": "ok" if count > 0 else "empty",
                "discarded_rows": discarded,
            }
    failed = [name for name, info in checks.items() if info["state"] == "skipped"]
    return {
        "ok": not failed,
        "tables": checks,
        "failed_tables": failed,
        "discarded_rows": sum(int(value or 0) for value in discarded_by_table.values()),
        "discarded_reason": "invalid_date",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def run_date_health_checks(client, database: str, tables) -> dict[str, Any]:
    """Detecta datos mal fechados en las tablas KPI ya cargadas en ClickHouse.

    Marca ``warn`` cuando una tabla tiene filas con la fecha épsilon
    (1970-01-01, el fallback histórico del transform) o un rango de fechas
    vacío (todas sus filas en la época). Las tablas sin filas son ``no_rows``
    (legítimo: un día sin datos) y no alertan. La intención es detectar
    automáticamente fechas sucias en origen sin romper el run: el warning
    queda en el reporte de calidad para que lo consuma la UI o un monitor.
    """
    from datetime import date as _date

    epoch = _date(1970, 1, 1)

    def _norm(value: Any) -> str | None:
        if value is None:
            return None
        if hasattr(value, "isoformat"):
            return value.isoformat()
        text = str(value)
        return text.split("T")[0] or None

    checks: dict[str, Any] = {}
    warned: list[str] = []
    for table in tables:
        try:
            rows = client.query(
                f"SELECT count(), countIf(date = '1970-01-01'), min(date), max(date) "
                f"FROM {database}.{table}"
            ).result_rows
            total, epoch_rows, min_date, max_date = rows[0]
            total = int(total or 0)
            epoch_rows = int(epoch_rows or 0)
            min_date = _norm(min_date)
            max_date = _norm(max_date)
            empty_range = total > 0 and (
                min_date is None
                or (min_date == "1970-01-01" and max_date == "1970-01-01")
            )
            if epoch_rows > 0 or empty_range:
                state = "warn"
                warned.append(table)
            elif total == 0:
                state = "no_rows"
            else:
                state = "ok"
            checks[table] = {
                "rows": total,
                "epoch_rows": epoch_rows,
                "min_date": min_date,
                "max_date": max_date,
                "empty_range": empty_range,
                "state": state,
            }
        except Exception as exc:  # pragma: no cover - tabla ausente o CH caído
            checks[table] = {
                "rows": 0,
                "epoch_rows": 0,
                "min_date": None,
                "max_date": None,
                "empty_range": True,
                "state": "error",
                "detail": str(exc),
            }
            warned.append(table)
    return {
        "ok": not warned,
        "tables": checks,
        "warned_tables": warned,
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
