from __future__ import annotations

import json

from config.settings import get_settings
from src.etl.schema import validate_columns


def validate_staged_schema() -> dict:
    settings = get_settings()
    metadata_path = settings.staging_dir / "extract_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    result = validate_columns(metadata["columns"])
    result["row_count"] = int(metadata["rows"])
    result["column_count"] = len(metadata["columns"])
    result["min_dataset_rows"] = settings.min_dataset_rows
    result["has_minimum_rows"] = result["row_count"] >= settings.min_dataset_rows
    result["has_minimum_columns"] = result["column_count"] > 12
    if not result["valid"]:
        raise ValueError(f"Invalid schema. Missing columns: {result['missing_columns']}")
    if not result["has_minimum_rows"]:
        raise ValueError(
            f"Dataset must have at least {settings.min_dataset_rows} rows. "
            f"Found: {result['row_count']}"
        )
    if not result["has_minimum_columns"]:
        raise ValueError(f"Dataset must have more than 12 columns. Found: {result['column_count']}")
    return result
