from __future__ import annotations

import json

import pandas as pd

from config.settings import get_settings


def extract_csv() -> dict:
    settings = get_settings()
    settings.staging_dir.mkdir(parents=True, exist_ok=True)
    if not settings.raw_csv_path.exists():
        raise FileNotFoundError(f"Raw CSV not found: {settings.raw_csv_path}")

    staging_path = settings.staging_dir / "hotels_extracted.jsonl"
    if staging_path.exists():
        staging_path.unlink()

    row_count = 0
    columns: list[str] = []
    for chunk in pd.read_csv(
        settings.raw_csv_path,
        dtype=str,
        keep_default_na=False,
        nrows=settings.demo_row_limit,
        chunksize=settings.chunk_size,
    ):
        if not columns:
            columns = list(chunk.columns)
        row_count += len(chunk)
        chunk.to_json(staging_path, orient="records", lines=True, force_ascii=False, mode="a")

    metadata = {
        "raw_csv_path": str(settings.raw_csv_path),
        "staging_path": str(staging_path),
        "rows": row_count,
        "row_limit": settings.demo_row_limit,
        "columns": columns,
        "chunk_size": settings.chunk_size,
    }
    (settings.staging_dir / "extract_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return metadata
