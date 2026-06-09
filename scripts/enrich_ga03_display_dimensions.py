from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from pymongo import MongoClient


load_dotenv()


DESTINATION_CATEGORIES = (
    "Destino urbano",
    "Destino playa",
    "Destino familiar",
    "Destino ejecutivo",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def mongo_database():
    client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    return client, client[os.getenv("MONGO_DATABASE", "hoteldata_hub")]


def clean_text(value) -> str:
    return str(value or "").strip()


def hotel_display_name(doc: dict) -> tuple[str, str, str | None]:
    prop_id = doc.get("prop_id")
    hotel_name = clean_text(doc.get("hotel_name")) or clean_text(doc.get("hotel_label"))
    if not hotel_name or hotel_name.lower() == "hotel no especificado":
        name = f"Hotel Partner {prop_id}"
    else:
        name = hotel_name
    stars = doc.get("prop_starrating")
    stars_label = f"{stars} estrellas" if stars not in (None, "") else "sin clasificacion"
    label = f"{name} · {stars_label}"
    country_id = doc.get("prop_country_id")
    country_label = f"Mercado hotelero {country_id}" if country_id not in (None, "") else None
    return name, label, country_label


def destination_display_name(doc: dict) -> tuple[str, str]:
    destination_id = int(doc["srch_destination_id"])
    category = DESTINATION_CATEGORIES[destination_id % 4]
    return f"{category} {destination_id}", category


def country_display_name(doc: dict) -> tuple[str, str]:
    country_id = doc.get("visitor_location_country_id")
    base_name = clean_text(doc.get("country_name")) or clean_text(doc.get("visitor_country_label"))
    name = base_name or f"Mercado visitante {country_id}"
    return name, f"Mercado {country_id}"


def site_display_name(doc: dict) -> tuple[str, str]:
    site_id = doc.get("site_id")
    base_name = clean_text(doc.get("site_name")) or clean_text(doc.get("site_label"))
    name = base_name or f"Canal Expedia {site_id}"
    return name, f"Canal {site_id}"


def ensure_indexes(db) -> None:
    db.dim_hotels.create_index("display_name")
    db.dim_hotels.create_index("manual_override")
    db.dim_destinations.create_index("destination_display_name")
    db.dim_visitor_countries.create_index("country_display_name")
    db.dim_sites.create_index("site_display_name")


def enrich_hotels(db) -> int:
    count = 0
    for doc in db.dim_hotels.find({}, {"_id": 1, "prop_id": 1, "hotel_name": 1, "hotel_label": 1, "prop_starrating": 1, "prop_country_id": 1, "display_name": 1, "manual_override": 1, "original_generated_name": 1}):
        display_name, display_label, display_country_label = hotel_display_name(doc)
        if doc.get("manual_override") is True:
            db.dim_hotels.update_one(
                {"_id": doc["_id"]},
                {
                    "$set": {
                        "display_label": display_label,
                        "display_country_label": display_country_label,
                        "demo_enriched": True,
                        "updated_at": utc_now(),
                        "original_generated_name": clean_text(doc.get("original_generated_name")) or clean_text(doc.get("display_name")) or display_name,
                    }
                },
            )
            count += 1
            continue
        db.dim_hotels.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "display_name": display_name,
                    "display_label": display_label,
                    "display_country_label": display_country_label,
                    "demo_enriched": True,
                    "manual_override": False,
                    "name_source": "generated_from_id",
                    "original_generated_name": clean_text(doc.get("original_generated_name")) or display_name,
                    "updated_at": utc_now(),
                }
            },
        )
        count += 1
    return count


def enrich_destinations(db) -> int:
    count = 0
    for doc in db.dim_destinations.find({}, {"_id": 1, "srch_destination_id": 1}):
        name, region = destination_display_name(doc)
        db.dim_destinations.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "destination_display_name": name,
                    "destination_region_label": region,
                    "demo_enriched": True,
                }
            },
        )
        count += 1
    return count


def enrich_countries(db) -> int:
    count = 0
    for doc in db.dim_visitor_countries.find({}, {"_id": 1, "visitor_location_country_id": 1, "country_name": 1, "visitor_country_label": 1}):
        name, market = country_display_name(doc)
        db.dim_visitor_countries.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "country_display_name": name,
                    "market_label": market,
                    "demo_enriched": True,
                }
            },
        )
        count += 1
    return count


def enrich_sites(db) -> int:
    count = 0
    for doc in db.dim_sites.find({}, {"_id": 1, "site_id": 1, "site_name": 1, "site_label": 1}):
        name, channel = site_display_name(doc)
        db.dim_sites.update_one(
            {"_id": doc["_id"]},
            {
                "$set": {
                    "site_display_name": name,
                    "channel_label": channel,
                    "demo_enriched": True,
                }
            },
        )
        count += 1
    return count


def main() -> None:
    client, db = mongo_database()
    try:
        ensure_indexes(db)
        report = {
            "ok": True,
            "database": db.name,
            "hotels_enriched": enrich_hotels(db),
            "destinations_enriched": enrich_destinations(db),
            "countries_enriched": enrich_countries(db),
            "sites_enriched": enrich_sites(db),
        }
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    finally:
        client.close()


if __name__ == "__main__":
    main()
