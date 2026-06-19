from __future__ import annotations

import json
import sys
from pathlib import Path


SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))
PROJECT_ROOT = Path(__file__).resolve().parents[2]

from src.database.connection import get_database
from src.app.modules.reservations.service import ensure_reservation_collections


def main() -> None:
    result = ensure_reservation_collections()
    db = get_database()
    counts = {name: db[name].count_documents({}) for name in result["collections"]}
    print(
        json.dumps(
            {
                "ok": True,
                "database": db.name,
                "collections": result["collections"],
                "counts": counts,
            },
            indent=2,
            ensure_ascii=True,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
