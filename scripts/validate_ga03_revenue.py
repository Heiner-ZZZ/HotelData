from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.app.modules.revenue.service import (
    create_promotion_campaign,
    create_rate_plan,
    ensure_revenue_collections,
    hotel_rates_overview,
    promotions_management_overview,
    rate_plans_overview,
    save_hotel_rate,
)
from src.database.connection import get_database


TEST_PROP_ID = 1
TEST_RATE_PLAN_ID = "RP-1-ga03-test-rate-plan"
TEST_CAMPAIGN_ID = "PC-1-ga03-test-campaign"


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    ensure_revenue_collections()
    db = get_database()

    before = {
        "rate_plans": db.rate_plans.count_documents({"prop_id": TEST_PROP_ID}),
        "hotel_rate_calendar": db.hotel_rate_calendar.count_documents({"prop_id": TEST_PROP_ID}),
        "rate_rules": db.rate_rules.count_documents({"prop_id": TEST_PROP_ID}),
        "promotion_campaigns": db.promotion_campaigns.count_documents({"prop_id": TEST_PROP_ID}),
        "coupon_codes": db.coupon_codes.count_documents({"prop_id": TEST_PROP_ID}),
    }

    create_rate_plan(
        prop_id=TEST_PROP_ID,
        name="GA03 Test Rate Plan",
        description="Plan de tarifa de prueba",
        base_rate=150,
        currency="USD",
        is_active=True,
    )
    save_hotel_rate(
        prop_id=TEST_PROP_ID,
        rate_plan_id=TEST_RATE_PLAN_ID,
        date="2026-06-25",
        rate_amount=175,
        min_stay_nights=2,
        is_closed=False,
    )
    create_promotion_campaign(
        prop_id=TEST_PROP_ID,
        name="GA03 Test Campaign",
        description="Campaña de prueba",
        discount_percent=15,
        start_date="2026-06-25",
        end_date="2026-06-30",
        coupon_code="GA03TEST15",
        is_active=True,
    )

    plans = rate_plans_overview()
    hotel_rates = hotel_rates_overview(TEST_PROP_ID)
    promotions = promotions_management_overview()

    db.hotel_rate_calendar.delete_many({"prop_id": TEST_PROP_ID, "rate_plan_id": TEST_RATE_PLAN_ID})
    db.rate_rules.delete_many({"prop_id": TEST_PROP_ID, "rate_plan_id": TEST_RATE_PLAN_ID})
    db.rate_plans.delete_many({"prop_id": TEST_PROP_ID, "rate_plan_id": TEST_RATE_PLAN_ID})
    db.coupon_codes.delete_many({"prop_id": TEST_PROP_ID, "campaign_id": TEST_CAMPAIGN_ID})
    db.promotion_campaigns.delete_many({"prop_id": TEST_PROP_ID, "campaign_id": TEST_CAMPAIGN_ID})

    after = {
        "rate_plans": db.rate_plans.count_documents({"prop_id": TEST_PROP_ID}),
        "hotel_rate_calendar": db.hotel_rate_calendar.count_documents({"prop_id": TEST_PROP_ID}),
        "rate_rules": db.rate_rules.count_documents({"prop_id": TEST_PROP_ID}),
        "promotion_campaigns": db.promotion_campaigns.count_documents({"prop_id": TEST_PROP_ID}),
        "coupon_codes": db.coupon_codes.count_documents({"prop_id": TEST_PROP_ID}),
    }

    report = {
        "ok": True,
        "before": before,
        "after_save": {
            "rate_plan_created": any(item["rate_plan_id"] == TEST_RATE_PLAN_ID for item in plans["items"]),
            "hotel_rate_created": any(item["rate_plan_id"] == TEST_RATE_PLAN_ID for item in hotel_rates["calendar"]),
            "promotion_created": any(item["campaign_id"] == TEST_CAMPAIGN_ID for item in promotions["campaigns"]),
            "promotion_impact_segments": len(promotions["impact"]["items"]),
        },
        "after_cleanup": after,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
