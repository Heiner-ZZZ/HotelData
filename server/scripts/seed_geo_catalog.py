"""
Seed geo_catalog with all country entries from dim_visitor_countries.

- Real country names (Bolivia, Bélgica, Perú) get proper ISO codes (BO, BE, PE).
- Generic placeholders ("Pais visitante N") get synthetic codes (XX-N).
- Existing geo_catalog entries are never overwritten.

Usage:
    docker compose -f infra/docker-compose.yml exec server python scripts/seed_geo_catalog.py
"""

from __future__ import annotations

import re
import sys
sys.path.insert(0, "/app")

from datetime import datetime, timezone
from config.settings import get_settings
from pymongo import MongoClient

settings = get_settings()
client: MongoClient = MongoClient(settings.mongo_uri)
db = client[settings.mongo_database]

# Known real country → ISO code mappings
REAL_COUNTRIES: dict[str, str] = {
    "Bolivia": "BO",
    "Bélgica": "BE",
    "Perú": "PE",
}

now = datetime.now(timezone.utc)
generic_pattern = re.compile(r"^Pais visitante (\d+)$", re.IGNORECASE)
existing_names = {d.get("name", "").strip().lower() for d in db.geo_catalog.find({"type": "country"}, {"name": 1})}
print(f"Existing geo_catalog countries: {len(existing_names)}")

inserted = 0
skipped = 0

for doc in db.dim_visitor_countries.find({}, {"visitor_location_country_id": 1, "visitor_country_label": 1, "country_display_name": 1}):
    vid = doc.get("visitor_location_country_id")
    label = doc.get("visitor_country_label", "")
    display = doc.get("country_display_name", "")
    name = display or label
    if not name:
        continue

    name_lower = name.strip().lower()
    if name_lower in existing_names:
        skipped += 1
        continue

    # Determine ISO code
    iso_code = REAL_COUNTRIES.get(name)
    if not iso_code:
        m = generic_pattern.match(name)
        if m:
            iso_code = f"XX-{m.group(1)}"
        else:
            # Unknown real name — generate a code from the name
            iso_code = name[:2].upper()

    db.geo_catalog.insert_one({
        "type": "country",
        "code": iso_code,
        "name": name.strip(),
        "created_at": now,
    })
    inserted += 1

total = db.geo_catalog.count_documents({"type": "country"})
print(f"Inserted: {inserted}, Skipped (already exist): {skipped}")
print(f"Total geo_catalog countries: {total}")
client.close()
print("Done.")
