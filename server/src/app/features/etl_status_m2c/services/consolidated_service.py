"""Estado consolidado del pipeline mongo_to_clickhouse para la UI.

Replica el contrato de ``/etl-status/consolidated`` (GA03) con identidad propia:
``/etl-status/m2c/consolidated``.
"""

from __future__ import annotations

from config.settings import get_settings
from src.app.features.etl_status_m2c.services.progress_service import m2c_progress
from src.app.features.etl_status_m2c.services.schedule_service import get_schedule
from src.etl.mongo_to_clickhouse.config import ALL_TABLES, paths
from src.etl.mongo_to_clickhouse._common import read_json_file


def _clickhouse_status() -> dict:
    settings = get_settings()
    try:
        import clickhouse_connect  # type: ignore

        client = clickhouse_connect.get_client(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            username=settings.clickhouse_user,
            password=settings.clickhouse_password,
            database=settings.clickhouse_database,
        )
        existing: list[str] = []
        try:
            rows = client.query("SHOW TABLES").result_rows
            existing = sorted({row[0] for row in rows if isinstance(row, (list, tuple)) and row})
        finally:
            client.close()
        tables = [
            {"name": name, "exists": name in existing}
            for name in ALL_TABLES
        ]
        return {
            "available": True,
            "database": settings.clickhouse_database,
            "tables": tables,
            "message": "ClickHouse disponible.",
        }
    except Exception as exc:  # pragma: no cover - depende de entorno
        return {
            "available": False,
            "database": settings.clickhouse_database,
            "tables": [{"name": name, "exists": False} for name in ALL_TABLES],
            "message": "No disponible.",
            "technical_detail": str(exc),
        }


def _execution_status() -> dict:
    report = read_json_file(paths()["execution_report"])
    return {
        "exists": bool(report),
        "path": str(paths()["execution_report"]),
        "payload": report,
    }


def consolidated() -> dict:
    return {
        "services": {
            "clickhouse": _clickhouse_status(),
        },
        "schedule": get_schedule(),
        "progress": m2c_progress(),
        "execution": _execution_status(),
    }
