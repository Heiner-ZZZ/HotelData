"""Seed: Add eligible_roles to existing rate plans.

This script migrates existing rate_plans to include the 'eligible_roles' field
with a sensible default based on the plan name and context:

- Rate plans named with "corporativo", "empresa", "business", "partner" → ["partner", "super_admin", "admin_sistema", "gerente_hotel"]
- All other rate plans → [] (eligible for all users)

Usage:
    docker exec hoteldata_server python /app/scripts/seed_rate_plan_eligibility.py
"""

from __future__ import annotations

import logging
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database.connection import get_database

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Role keywords that indicate a corporate/business rate plan
CORPORATE_KEYWORDS = ["corporativo", "empresa", "business", "partner", "corp"]

# Default eligible roles for corporate plans
CORPORATE_ROLES = ["partner", "super_admin", "admin_sistema", "gerente_hotel"]


def seed_rate_plan_eligibility() -> int:
    db = get_database()
    total = db.rate_plans.count_documents({})
    updated = 0

    plans = list(db.rate_plans.find({}, {"_id": 0, "rate_plan_id": 1, "name": 1, "eligible_roles": 1}))

    for plan in plans:
        # Skip if already has eligible_roles defined
        if "eligible_roles" in plan and plan.get("eligible_roles") is not None:
            continue

        name_lower = (plan.get("name") or "").lower()
        is_corporate = any(kw in name_lower for kw in CORPORATE_KEYWORDS)
        roles = list(CORPORATE_ROLES) if is_corporate else []

        db.rate_plans.update_one(
            {"rate_plan_id": plan["rate_plan_id"]},
            {"$set": {"eligible_roles": roles}},
        )
        updated += 1
        label = "corporativo" if is_corporate else "público"
        logger.info(
            "  [%s] %s → roles=%s (%s)",
            plan["rate_plan_id"],
            plan.get("name", "?"),
            roles or "todos",
            label,
        )

    logger.info("Actualizados %d de %d planes tarifarios.", updated, total)
    return updated


if __name__ == "__main__":
    count = seed_rate_plan_eligibility()
    print(f"\n✅ {count} plan(es) actualizado(s) con eligible_roles.")
