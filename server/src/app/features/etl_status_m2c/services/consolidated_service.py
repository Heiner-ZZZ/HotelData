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


def _dato_status() -> dict:
    """Directorio Dato: ruta visible + conteos parquet de la última corrida.

    ``root`` es la ruta del host (Windows) que ve el usuario; la UI la muestra
    para navegar a los .parquet. Los conteos por sección vienen del registro
    que el pipeline escribe en cada corrida (``m2c_dato_export.json``).
    """
    settings = get_settings()
    record = read_json_file(paths()["dato_export_json"])
    return {
        "exists": bool(record),
        "root": str(settings.dato_dir_host),
        "container_path": str(settings.dato_dir),
        "run_date": record.get("run_date", ""),
        "sections": record.get("sections", {}),
        "generated_at": record.get("generated_at", ""),
    }


def consolidated() -> dict:
    return {
        "services": {
            "clickhouse": _clickhouse_status(),
        },
        "schedule": get_schedule(),
        "progress": m2c_progress(),
        "execution": _execution_status(),
        "dato": _dato_status(),
    }
