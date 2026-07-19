"""Enrich dim_hotels for props 1-5 with real display data so the welcome page
featured hotels section shows proper hotel cards (name, city, country, stars).

These 5 hotels already have hotel_content_pages with amenities/descriptions
and hotel_images + inventory. This script fills in the missing dim_hotels fields.
"""

import os
from datetime import datetime, timezone

from pymongo import MongoClient

uri = os.environ.get("MONGO_URI")
db_name = os.environ.get("MONGO_DATABASE", "hoteldata_hub")

HOTELS = [
    {
        "prop_id": 1,
        "display_name": "Hotel Lima Centro",
        "hotel_name": "Hotel Lima Centro",
        "hotel_label": "Hotel Lima Centro",
        "prop_starrating": 4,
        "prop_review_score": 4.6,
        "prop_location_score1": 4.5,
        "prop_country_id": 169,  # PE
        "display_country_label": "Perú",
        "city": "Lima",
        "manual_override": True,
        "name_source": "manual",
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f"),
        "updated_by": "seed_featured_hotels",
    },
    {
        "prop_id": 2,
        "display_name": "Resort Cancún Playa",
        "hotel_name": "Resort Cancún Playa",
        "hotel_label": "Resort Cancún Playa",
        "prop_starrating": 5,
        "prop_review_score": 4.8,
        "prop_location_score1": 5.5,
        "prop_country_id": 142,  # MX
        "display_country_label": "México",
        "city": "Cancún",
        "manual_override": True,
        "name_source": "manual",
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f"),
        "updated_by": "seed_featured_hotels",
    },
    {
        "prop_id": 3,
        "display_name": "Hotel Quito Histórico",
        "hotel_name": "Hotel Quito Histórico",
        "hotel_label": "Hotel Quito Histórico",
        "prop_starrating": 3,
        "prop_review_score": 4.2,
        "prop_location_score1": 3.8,
        "prop_country_id": 60,  # EC
        "display_country_label": "Ecuador",
        "city": "Quito",
        "manual_override": True,
        "name_source": "manual",
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f"),
        "updated_by": "seed_featured_hotels",
    },
    {
        "prop_id": 4,
        "display_name": "Hotel Buenos Aires Elegance",
        "hotel_name": "Hotel Buenos Aires Elegance",
        "hotel_label": "Hotel Buenos Aires Elegance",
        "prop_starrating": 4,
        "prop_review_score": 4.5,
        "prop_location_score1": 4.8,
        "prop_country_id": 10,  # AR
        "display_country_label": "Argentina",
        "city": "Buenos Aires",
        "manual_override": True,
        "name_source": "manual",
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f"),
        "updated_by": "seed_featured_hotels",
    },
    {
        "prop_id": 5,
        "display_name": "Hotel Santiago Business",
        "hotel_name": "Hotel Santiago Business",
        "hotel_label": "Hotel Santiago Business",
        "prop_starrating": 4,
        "prop_review_score": 4.3,
        "prop_location_score1": 4.2,
        "prop_country_id": 45,  # CL
        "display_country_label": "Chile",
        "city": "Santiago",
        "manual_override": True,
        "name_source": "manual",
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f"),
        "updated_by": "seed_featured_hotels",
    },
]


def seed():
    c = MongoClient(uri, serverSelectionTimeoutMS=5000)
    db = c[db_name]

    for hotel_data in HOTELS:
        pid = hotel_data["prop_id"]
        result = db.dim_hotels.update_one(
            {"prop_id": pid},
            {"$set": hotel_data},
        )
        status = "updated" if result.matched_count else "not found"
        print(f"  prop_id={pid} ({hotel_data['display_name']}): {status} "
              f"(matched={result.matched_count}, modified={result.modified_count})")

    # Verify
    print("\n=== Verification ===")
    for d in db.dim_hotels.find(
        {"prop_id": {"$in": [h["prop_id"] for h in HOTELS]}},
        {"_id": 0, "prop_id": 1, "display_name": 1, "city": 1,
         "display_country_label": 1, "prop_starrating": 1, "prop_review_score": 1},
    ).sort("prop_id", 1):
        print(f"  prop_id={d['prop_id']}: name={d.get('display_name','?')} "
              f"city={d.get('city','?')} country={d.get('display_country_label','?')} "
              f"stars={d.get('prop_starrating','?')} score={d.get('prop_review_score','?')}")

    c.close()
    print("\nDone.")


if __name__ == "__main__":
    seed()
