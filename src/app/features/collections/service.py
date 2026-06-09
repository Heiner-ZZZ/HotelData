from __future__ import annotations

from src.database.connection import get_database
from src.database.repositories import DATASET_COLLECTIONS, MASTER_COLLECTIONS, REJECTED_COLLECTIONS


def collection_counts() -> dict[str, int]:
    db = get_database()
    names = MASTER_COLLECTIONS + DATASET_COLLECTIONS + REJECTED_COLLECTIONS + [
        "data_quality_reports",
        "etl_executions",
        "search_logs",
        "system_catalogs",
    ]
    return {name: db[name].count_documents({}) for name in names}
