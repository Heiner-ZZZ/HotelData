from __future__ import annotations

import json
import re

import pandas as pd

from config.settings import get_settings
from src.etl.schema import EXPECTED_COLUMNS


NULL_MARKERS = {"", "nan", "none", "null", "n/a", "na", "-"}


def _clean_string(value: object) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    if text.lower() in NULL_MARKERS:
        return None
    return text


def _normalize_rating(value: object) -> float | None:
    text = _clean_string(value)
    if text is None:
        return None
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None
    rating = float(match.group(0))
    if rating > 5 and rating <= 50:
        rating = rating / 10
    if rating < 0:
        return None
    return min(rating, 5.0)


def _prepare_chunk(dataframe: pd.DataFrame) -> pd.DataFrame:
    for column in EXPECTED_COLUMNS:
        if column not in dataframe.columns:
            dataframe[column] = None
    dataframe = dataframe[EXPECTED_COLUMNS].copy()
    for column in EXPECTED_COLUMNS:
        if column != "HotelRating":
            dataframe[column] = dataframe[column].map(_clean_string)
    dataframe["HotelRating"] = dataframe["HotelRating"].map(_normalize_rating)
    dataframe["HotelCode"] = dataframe["HotelCode"].map(_clean_string)
    return dataframe


def transform_clean_dataset() -> dict:
    settings = get_settings()
    staging_path = settings.staging_dir / "hotels_extracted.jsonl"
    cleaned_path = settings.processed_dir / "hotels_clean.jsonl"
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    if cleaned_path.exists():
        cleaned_path.unlink()

    seen_hotel_codes: set[str] = set()
    input_rows = 0
    output_rows = 0
    missing_hotel_code_rows = 0
    duplicate_hotel_code_rows = 0
    nulls_by_column = {column: 0 for column in EXPECTED_COLUMNS}

    for chunk in pd.read_json(staging_path, lines=True, dtype=False, chunksize=settings.chunk_size):
        input_rows += len(chunk)
        chunk = _prepare_chunk(chunk)
        missing_hotel_code_rows += int(chunk["HotelCode"].isna().sum())
        chunk = chunk.dropna(subset=["HotelCode"])
        duplicate_mask = chunk["HotelCode"].duplicated(keep="first") | chunk["HotelCode"].isin(seen_hotel_codes)
        duplicate_hotel_code_rows += int(duplicate_mask.sum())
        chunk = chunk.loc[~duplicate_mask]
        seen_hotel_codes.update(chunk["HotelCode"].tolist())
        output_rows += len(chunk)
        for column in EXPECTED_COLUMNS:
            nulls_by_column[column] += int(chunk[column].isna().sum())
        chunk.to_json(cleaned_path, orient="records", lines=True, force_ascii=False, mode="a")

    total_cells = output_rows * len(EXPECTED_COLUMNS)
    total_nulls = sum(nulls_by_column.values())
    report = {
        "input_rows": input_rows,
        "output_rows": output_rows,
        "missing_hotel_code_rows": missing_hotel_code_rows,
        "duplicate_hotel_code_rows": duplicate_hotel_code_rows,
        "nulls_by_column": nulls_by_column,
        "completeness_score": round(1 - (total_nulls / total_cells), 4) if total_cells else 0,
        "cleaned_path": str(cleaned_path),
    }
    (settings.reports_dir / "cleaning_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return report
