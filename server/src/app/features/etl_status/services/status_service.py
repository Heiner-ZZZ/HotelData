from __future__ import annotations

import json

from config.settings import get_settings
from src.database.connection import get_database


def artifact_status() -> dict:
    settings = get_settings()
    parquet_path = settings.project_root / "data" / "processed" / "reservas_hoteleras_03.parquet"
    jsonl_path = settings.project_root / "data" / "staging" / "reservas_hoteleras_03_extract.jsonl"
    return {
        "jsonl": {
            "exists": jsonl_path.exists(),
            "path": str(jsonl_path),
        },
        "parquet": {
            "exists": parquet_path.exists(),
            "path": str(parquet_path),
        },
    }


def mongodb_status() -> dict:
    settings = get_settings()
    try:
        db = get_database()
        db.command("ping")
        collections = db.list_collection_names()
        fact_exists = "fact_hotel_reservations" in collections
        fact_count = db.fact_hotel_reservations.count_documents({}) if fact_exists else 0
        ga03_count = db.fact_hotel_reservations.count_documents({"phase": "GA03"}) if fact_exists else 0
        return {
            "available": True,
            "database": settings.mongo_database,
            "fact_exists": fact_exists,
            "fact_count": fact_count,
            "ga03_fact_count": ga03_count,
            "message": "MongoDB disponible.",
        }
    except Exception as exc:
        return {
            "available": False,
            "database": settings.mongo_database,
            "fact_exists": False,
            "fact_count": None,
            "ga03_fact_count": None,
            "message": "No disponible.",
            "technical_detail": str(exc),
        }


def report_status() -> dict:
    settings = get_settings()
    report_files = {
        "progress": settings.reports_dir / "progreso_preparacion_reservas_03.json",
        "pipeline_progress": settings.reports_dir / "progreso_pipeline_reservas_03.json",
        "validation": settings.reports_dir / "validacion_dataset_reservas_03.json",
        "quality": settings.reports_dir / "reporte_calidad_reservas_03.json",
        "execution": settings.reports_dir / "reporte_ejecucion_reservas_03.json",
    }
    reports = {}
    for name, path in report_files.items():
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {"error": "JSON inválido"}
            reports[name] = {
                "exists": True,
                "path": str(path),
                "payload": payload,
            }
        else:
            reports[name] = {
                "exists": False,
                "path": str(path),
                "payload": {},
            }
    return reports
