from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.app.modules.partner.services import ensure_hotel_content_collections
from src.database.connection import get_database


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")

    summary = ensure_hotel_content_collections()
    db = get_database()
    counts = {
        "hotel_images": db.hotel_images.count_documents({}),
        "hotel_policies": db.hotel_policies.count_documents({}),
        "hotel_content_pages": db.hotel_content_pages.count_documents({}),
        "hotel_content_changes": db.hotel_content_changes.count_documents({}),
    }
    print(
        json.dumps(
            {
                "database": db.name,
                "created_collections": summary["collections"],
                "indexes_verified": summary["indexes"],
                "counts": counts,
            },
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
