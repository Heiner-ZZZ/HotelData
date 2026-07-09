from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database.connection import get_database


DEFAULTS = {
    "quality_levels": [
        {"catalog_type": "quality_levels", "code": "QUALITY_HIGH", "label": "Alta calidad"},
        {"catalog_type": "quality_levels", "code": "QUALITY_MEDIUM", "label": "Calidad media"},
        {"catalog_type": "quality_levels", "code": "QUALITY_LOW", "label": "Baja calidad"},
    ],
    "issue_types": [
        {"catalog_type": "issue_types", "code": "MISSING_CONTACT", "label": "Falta contacto"},
    ],
    "status_flags": [
        {"catalog_type": "status_flags", "code": "ACTIVE", "label": "Activo"},
        {"catalog_type": "status_flags", "code": "INACTIVE", "label": "Inactivo"},
    ],
    "metric_groups": [
        {"catalog_type": "metric_groups", "code": "DEFAULT", "label": "Default"},
    ],
}


def main() -> None:
    db = get_database()
    now = datetime.now(timezone.utc)
    for cat_type, items in DEFAULTS.items():
        for item in items:
            doc = {**item, "created_at": now, "updated_at": now}
            db.system_catalogs.update_one(
                {"catalog_type": doc["catalog_type"], "code": doc["code"]},
                {"$setOnInsert": doc},
                upsert=True,
            )

    print("Semilla de system_catalogs completada.")


if __name__ == "__main__":
    main()
