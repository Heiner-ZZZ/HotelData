from __future__ import annotations

from src.etl.schema import EXPECTED_COLUMNS, validate_columns


def test_expected_schema_is_valid():
    result = validate_columns(EXPECTED_COLUMNS)
    assert result["valid"] is True
    assert result["missing_columns"] == []


def test_missing_schema_column_is_invalid():
    result = validate_columns(EXPECTED_COLUMNS[:-1])
    assert result["valid"] is False
    assert result["missing_columns"] == ["price_usd"]
