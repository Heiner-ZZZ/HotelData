from __future__ import annotations

import csv
from pathlib import Path

from config.settings import get_settings


def raw_file_status() -> dict:
    settings = get_settings()
    raw_path = settings.raw_csv_path
    if not raw_path.exists():
        return {
            "exists": False,
            "path": str(raw_path),
            "filename": raw_path.name,
            "rows": 0,
            "actual_rows": 0,
            "demo_row_limit": settings.demo_row_limit,
            "columns": [],
        }

    with raw_path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.reader(source)
        try:
            columns = next(reader)
        except StopIteration:
            columns = []
            row_count = 0
        else:
            row_count = 0
            for _ in reader:
                row_count += 1
                if row_count >= settings.demo_row_limit:
                    break

    demo_rows = min(row_count, settings.demo_row_limit)
    actual_rows = demo_rows if row_count < settings.demo_row_limit else f">= {settings.demo_row_limit}"

    return {
        "exists": True,
        "path": str(raw_path),
        "filename": raw_path.name,
        "rows": demo_rows,
        "actual_rows": actual_rows,
        "demo_row_limit": settings.demo_row_limit,
        "columns": columns,
    }


def save_uploaded_raw_csv(filename: str, content: bytes) -> dict:
    settings = get_settings()
    raw_path = settings.raw_csv_path
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(content)
    status = raw_file_status()
    status["uploaded_filename"] = Path(filename).name
    return status


def save_ga03_source_csv(filename: str, content: bytes) -> dict:
    settings = get_settings()
    upload_path = settings.project_root / "data" / "uploads" / "ga03_source.csv"
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    upload_path.write_bytes(content)
    return {
        "uploaded_filename": Path(filename).name,
        "path": str(upload_path),
        "exists": upload_path.exists(),
    }
