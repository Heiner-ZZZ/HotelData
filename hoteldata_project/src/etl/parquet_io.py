from __future__ import annotations

import pandas as pd

from config.settings import get_settings


def convert_pocketbase_staging_to_parquet() -> dict:
    settings = get_settings()
    source = settings.staging_dir / "pocketbase_reservations.jsonl"
    target = settings.reservations_parquet_path
    if not source.exists():
        raise FileNotFoundError(f"PocketBase staging file not found: {source}")

    rows = 0
    frames = []
    for chunk in pd.read_json(source, lines=True, dtype=False, chunksize=settings.chunk_size):
        rows += len(chunk)
        frames.append(chunk)

    dataframe = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    target.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_parquet(target, index=False)
    return {"parquet_path": str(target), "rows": rows, "columns": list(dataframe.columns)}


def read_reservations_parquet() -> pd.DataFrame:
    settings = get_settings()
    if not settings.reservations_parquet_path.exists():
        raise FileNotFoundError(f"Reservations Parquet file not found: {settings.reservations_parquet_path}")
    return pd.read_parquet(settings.reservations_parquet_path)
