from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))
PROJECT_ROOT = Path(__file__).resolve().parents[2]

from src.app.modules.revenue.service import ensure_revenue_collections
from src.database.connection import get_database


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    summary = ensure_revenue_collections()
    db = get_database()
    counts = {
        "rate_plans": db.rate_plans.count_documents({}),
        "hotel_rate_calendar": db.hotel_rate_calendar.count_documents({}),
        "rate_rules": db.rate_rules.count_documents({}),
        "promotion_campaigns": db.promotion_campaigns.count_documents({}),
        "coupon_codes": db.coupon_codes.count_documents({}),
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
