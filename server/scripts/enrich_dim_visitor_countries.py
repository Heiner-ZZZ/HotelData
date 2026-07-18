"""Enrich `dim_visitor_countries.country_display_name` with real locale names.

Idempotent (uses `$set`, runs cleanly on repeat). Updates three fields at
once so every display path renders the Spanish name:

  • `country_display_name`  — what the new `/api/public/countries`
                              onboarding endpoint returns + the most-common
                              adapter in `partner/_common.py`.
  • `country_name`          — older adapter & dashboard joins.
  • `visitor_country_label` — admin UI label fallback.

Adds an `enriched_at` ISO timestamp per row for auditability.

Run inside the docker network (server container has the right env):
    docker exec hoteldata_server python -m scripts.enrich_dim_visitor_countries

Or from outside if the host can reach mongo at `mongodb://mongo:27018`:
    cd server && python -m scripts.enrich_dim_visitor_countries

Extend `COUNTRY_ENRICHMENTS` as the admin learns more ID→name mappings. IDs
not present in the collection are reported as `skipped` (and don't raise).
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database.connection import get_database  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# ── Best-effort LATAM mapping ────────────────────────────────────────
#
# The seed CSV's `visitor_location_country_id` column holds raw Expedia-style
# numeric IDs that don't follow ISO 3166-1. Only a handful of seeded rows
# carry a real name (we know id=2 → Bolivia, id=219 → Perú from prior smoke-
# tests); the rest are the seed default "País visitante N". As admins fill
# in the rest via `PUT /api/geo/visitor-countries/{id}` (existing in
# modules/geo_catalog/routes.py), extend the dict below OR keep the admin
# route as the canonical entrypoint. This script only does the bulk seed
# step; per-row deletions are best handled via the admin endpoint.
# ─────────────────────────────────────────────────────────────────────

COUNTRY_ENRICHMENTS: dict[int, str] = {
    2: "Bolivia",
    # id=4 is "BÉLGICA" — kept verbatim because it's a real seeded entry
    # for European visitors; renames the casing to a Spanish canonical.
    4: "Bélgica",
    219: "Perú",
}


def main() -> None:
    db = get_database()
    upserts = 0
    skipped = 0
    now = datetime.now(timezone.utc).isoformat()

    for country_id, display_name in COUNTRY_ENRICHMENTS.items():
        result = db.dim_visitor_countries.update_one(
            {"visitor_location_country_id": country_id},
            {
                "$set": {
                    "country_display_name": display_name,
                    "country_name": display_name,
                    "visitor_country_label": display_name,
                    "enriched_at": now,
                }
            },
        )
        if result.matched_count == 0:
            logger.warning("id=%s not found in dim_visitor_countries — skipped", country_id)
            skipped += 1
        else:
            logger.info("id=%s -> %r", country_id, display_name)
            upserts += 1

    total = db.dim_visitor_countries.count_documents({})
    logger.info(
        "Enrichment complete: %s upserted, %s skipped; collection total=%s",
        upserts,
        skipped,
        total,
    )


if __name__ == "__main__":
    main()
