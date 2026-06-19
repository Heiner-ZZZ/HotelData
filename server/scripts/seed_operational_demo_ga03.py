from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database.connection import get_database


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "seed_operational_demo_ga03.json"
SEED_SOURCE = "ga03_operational_seed"
TARGET_COLLECTIONS = [
    "room_types",
    "hotel_rooms",
    "room_inventory_calendar",
    "rate_plans",
    "hotel_rate_calendar",
    "hotel_policies",
    "hotel_content_pages",
    "hotel_images",
    "promotion_campaigns",
    "coupon_codes",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def iso_date(days_from_today: int) -> str:
    return (date.today() + timedelta(days=days_from_today)).isoformat()


def hotel_display_name(hotel: dict[str, Any], prop_id: int) -> str:
    return hotel.get("display_name") or hotel.get("hotel_name") or hotel.get("hotel_label") or f"Hotel Partner {prop_id}"


def ensure_collections_exist(db) -> None:
    existing = set(db.list_collection_names())
    missing = [name for name in TARGET_COLLECTIONS if name not in existing]
    if missing:
        raise SystemExit(f"Faltan colecciones para seed operativo demo: {', '.join(missing)}")


def before_counts(db) -> dict[str, int]:
    return {name: int(db[name].count_documents({})) for name in TARGET_COLLECTIONS}


def seed_room_type(db, prop_id: int, hotel_name: str, spec: dict[str, Any]) -> dict[str, Any]:
    room_type_id = f"RT-{prop_id}-{spec['slug']}"
    payload = {
        "room_type_id": room_type_id,
        "prop_id": prop_id,
        "name": spec["name"],
        "description": f"{spec['name']} demo para {hotel_name}",
        "base_capacity": spec["base_capacity"],
        "max_adults": spec["max_adults"],
        "max_children": spec["max_children"],
        "is_active": True,
        "demo_seed": True,
        "source": SEED_SOURCE,
        "updated_at": utc_now(),
    }
    db.room_types.update_one(
        {"room_type_id": room_type_id},
        {"$set": payload, "$setOnInsert": {"created_at": utc_now()}},
        upsert=True,
    )
    db.hotel_rooms.update_one(
        {"hotel_room_id": f"HR-{room_type_id}"},
        {
            "$set": {
                "hotel_room_id": f"HR-{room_type_id}",
                "prop_id": prop_id,
                "room_type_id": room_type_id,
                "room_label": spec["name"],
                "is_active": True,
                "demo_seed": True,
                "source": SEED_SOURCE,
                "updated_at": utc_now(),
            },
            "$setOnInsert": {"created_at": utc_now()},
        },
        upsert=True,
    )
    for day_offset in range(7):
        total_rooms = spec["inventory_total"]
        blocked_rooms = 1 if day_offset == 5 else 0
        available_rooms = max(total_rooms - blocked_rooms - (day_offset % 2), 0)
        db.room_inventory_calendar.update_one(
            {"prop_id": prop_id, "room_type_id": room_type_id, "date": iso_date(day_offset)},
            {
                "$set": {
                    "prop_id": prop_id,
                    "room_type_id": room_type_id,
                    "date": iso_date(day_offset),
                    "total_rooms": total_rooms,
                    "available_rooms": available_rooms,
                    "blocked_rooms": blocked_rooms,
                    "demo_seed": True,
                    "source": SEED_SOURCE,
                    "updated_at": utc_now(),
                },
                "$setOnInsert": {"created_at": utc_now()},
            },
            upsert=True,
        )
    return {"room_type_id": room_type_id, "days_seeded": 7}


def seed_rate_plan(db, prop_id: int, hotel_name: str, spec: dict[str, Any]) -> dict[str, Any]:
    rate_plan_id = f"RP-{prop_id}-{spec['slug']}"
    payload = {
        "rate_plan_id": rate_plan_id,
        "prop_id": prop_id,
        "name": spec["name"],
        "description": f"{spec['name']} demo para {hotel_name}",
        "base_rate": spec["base_rate"],
        "currency": "USD",
        "is_active": True,
        "demo_seed": True,
        "source": SEED_SOURCE,
        "updated_at": utc_now(),
    }
    db.rate_plans.update_one(
        {"rate_plan_id": rate_plan_id},
        {"$set": payload, "$setOnInsert": {"created_at": utc_now()}},
        upsert=True,
    )
    for day_offset in range(7):
        db.hotel_rate_calendar.update_one(
            {"prop_id": prop_id, "rate_plan_id": rate_plan_id, "date": iso_date(day_offset)},
            {
                "$set": {
                    "prop_id": prop_id,
                    "rate_plan_id": rate_plan_id,
                    "date": iso_date(day_offset),
                    "rate_amount": round(spec["base_rate"] + (day_offset * spec["delta"]), 2),
                    "min_stay_nights": 1 if spec["slug"] == "flex" else 2,
                    "is_closed": False,
                    "demo_seed": True,
                    "source": SEED_SOURCE,
                    "updated_at": utc_now(),
                },
                "$setOnInsert": {"created_at": utc_now()},
            },
            upsert=True,
        )
    return {"rate_plan_id": rate_plan_id, "days_seeded": 7}


def seed_content_documents(db, prop_id: int, hotel_name: str) -> None:
    db.hotel_policies.update_one(
        {"prop_id": prop_id},
        {
            "$set": {
                "prop_id": prop_id,
                "check_in_time": "15:00",
                "check_out_time": "12:00",
                "cancellation_policy": "Cancelación gratuita hasta 48 horas antes.",
                "pet_policy": "Mascotas permitidas con recargo.",
                "children_policy": "Niños hasta 12 años pueden compartir habitación.",
                "extra_bed_policy": "Sujeto a disponibilidad.",
                "payment_policy": "Tarjeta garantizada al reservar.",
                "house_rules": "No fumar en habitaciones interiores.",
                "demo_seed": True,
                "source": SEED_SOURCE,
                "updated_at": utc_now(),
            },
            "$setOnInsert": {"created_at": utc_now()},
        },
        upsert=True,
    )
    db.hotel_content_pages.update_one(
        {"prop_id": prop_id},
        {
            "$set": {
                "prop_id": prop_id,
                "description": f"{hotel_name} cuenta con contenido demo operativo para validar el módulo partner.",
                "highlights": "Ubicación estratégica\nAtención 24 horas\nTarifas dinámicas",
                "amenities_text": "Wi-Fi, Desayuno, Piscina, Gimnasio",
                "active_amenities": ["Wi-Fi", "Desayuno incluido", "Piscina", "Gimnasio"],
                "amenities_catalog": [
                    {"category": "General", "label": "Wi-Fi"},
                    {"category": "Gastronomia", "label": "Desayuno incluido"},
                    {"category": "Bienestar", "label": "Piscina"},
                    {"category": "Bienestar", "label": "Gimnasio"},
                ],
                "demo_seed": True,
                "source": SEED_SOURCE,
                "updated_at": utc_now(),
            },
            "$setOnInsert": {"created_at": utc_now()},
        },
        upsert=True,
    )
    for image_number in range(1, 3):
        image_url = f"https://demo.hoteldata.local/images/hotel-{prop_id}-{image_number}.jpg"
        db.hotel_images.update_one(
            {"prop_id": prop_id, "image_url": image_url},
            {
                "$set": {
                    "prop_id": prop_id,
                    "image_url": image_url,
                    "title": f"{hotel_name} imagen demo {image_number}",
                    "demo_seed": True,
                    "source": SEED_SOURCE,
                    "updated_at": utc_now(),
                },
                "$setOnInsert": {"created_at": utc_now()},
            },
            upsert=True,
        )


def seed_promotion_documents(db, prop_id: int, hotel_name: str) -> dict[str, str]:
    campaign_id = f"PC-{prop_id}-demo-campaign"
    coupon_code = f"GA03-{prop_id}-DEMO"
    db.promotion_campaigns.update_one(
        {"campaign_id": campaign_id},
        {
            "$set": {
                "campaign_id": campaign_id,
                "prop_id": prop_id,
                "name": f"Promo demo {hotel_name}",
                "description": "Campaña operativa demo para pruebas de revenue.",
                "discount_percent": 12,
                "start_date": iso_date(0),
                "end_date": iso_date(6),
                "is_active": True,
                "demo_seed": True,
                "source": SEED_SOURCE,
                "updated_at": utc_now(),
            },
            "$setOnInsert": {"created_at": utc_now()},
        },
        upsert=True,
    )
    db.coupon_codes.update_one(
        {"coupon_code": coupon_code},
        {
            "$set": {
                "coupon_code": coupon_code,
                "campaign_id": campaign_id,
                "prop_id": prop_id,
                "discount_percent": 12,
                "is_active": True,
                "demo_seed": True,
                "source": SEED_SOURCE,
                "updated_at": utc_now(),
            },
            "$setOnInsert": {"created_at": utc_now()},
        },
        upsert=True,
    )
    return {"campaign_id": campaign_id, "coupon_code": coupon_code}


def main() -> int:
    db = get_database()
    ensure_collections_exist(db)
    before = before_counts(db)
    hotels = list(
        db.dim_hotels.find({}, {"_id": 0, "prop_id": 1, "display_name": 1, "hotel_name": 1, "hotel_label": 1})
        .sort("prop_id", 1)
        .limit(5)
    )
    if len(hotels) < 5:
        raise SystemExit("No hay suficientes hoteles en dim_hotels para sembrar el demo operativo.")

    room_type_specs = [
        {"slug": "standard", "name": "Habitación Standard Demo", "base_capacity": 2, "max_adults": 2, "max_children": 1, "inventory_total": 12},
        {"slug": "deluxe", "name": "Habitación Deluxe Demo", "base_capacity": 3, "max_adults": 3, "max_children": 1, "inventory_total": 8},
    ]
    rate_plan_specs = [
        {"slug": "flex", "name": "Tarifa Flexible Demo", "base_rate": 109.0, "delta": 3.5},
        {"slug": "advance", "name": "Tarifa Anticipada Demo", "base_rate": 94.0, "delta": 2.0},
    ]

    seeded_hotels: list[dict[str, Any]] = []
    for hotel in hotels:
        prop_id = int(hotel["prop_id"])
        name = hotel_display_name(hotel, prop_id)
        room_types = [seed_room_type(db, prop_id, name, spec) for spec in room_type_specs]
        rate_plans = [seed_rate_plan(db, prop_id, name, spec) for spec in rate_plan_specs]
        seed_content_documents(db, prop_id, name)
        promo = seed_promotion_documents(db, prop_id, name)
        seeded_hotels.append(
            {
                "prop_id": prop_id,
                "hotel_name": name,
                "room_types": room_types,
                "rate_plans": rate_plans,
                "promotion": promo,
            }
        )

    after = before_counts(db)
    report = {
        "generated_at": utc_now_iso(),
        "seed_source": SEED_SOURCE,
        "selected_prop_ids": [int(hotel["prop_id"]) for hotel in hotels],
        "before_counts": before,
        "after_counts": after,
        "delta_counts": {name: after[name] - before[name] for name in TARGET_COLLECTIONS},
        "seeded_hotels": seeded_hotels,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    print(f"report_path={REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
