from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import get_settings
from src.etl.schema import validate_columns


def main() -> None:
    settings = get_settings()
    dataframe = pd.read_csv(settings.raw_csv_path, dtype=str, keep_default_na=False)
    print(f"Path: {settings.raw_csv_path}")
    print(f"Rows: {len(dataframe)}")
    print(f"Columns: {len(dataframe.columns)}")
    print(validate_columns(list(dataframe.columns)))


if __name__ == "__main__":
    main()
