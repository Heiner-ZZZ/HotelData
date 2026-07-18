from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.etl.tasks import (
    create_indexes,
    extract_csv,
    load_business_collections,
    load_fact_events,
    load_rejected_records,
    save_execution_report,
    seed_master_collections_check,
    transform_business_collections,
    transform_clean_dataset,
    transform_dataset_container,
    transform_fact_events,
    validate_environment,
    validate_master_keys,
    validate_schema,
)


def main() -> None:
    steps = [
        validate_environment,
        seed_master_collections_check,
        extract_csv,
        validate_schema,
        transform_clean_dataset,
        transform_dataset_container,
        transform_business_collections,
        load_business_collections,
        transform_fact_events,
        validate_master_keys,
        load_fact_events,
        load_rejected_records,
        create_indexes,
        save_execution_report,
    ]
    for step in steps:
        print(f"Running {step.__name__}")
        print(step())


if __name__ == "__main__":
    main()
