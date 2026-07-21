"""Seed operational data needed for booking: hotels, room types, inventory, rates.

This script works WITHOUT the raw hotels.csv — it creates hardcoded demo data
so the booking flow has inventory to validate against.
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database.connection import get_database
from src.database.indexes import create_indexes


SEED_SOURCE = "booking_seed"
NUM_HOTELS = 10
NUM_ROOM_TYPES = 3
NUM_RATE_PLANS = 2
FORECAST_DAYS = 120
REPORT_PATH = Path(__file__).resolve().parents[2] / "data" / "reports" / "seed_booking_data.json"


HOTEL_NAMES = [
    "Grand Palace Resort",
    "Ocean View Hotel",
    "Mountain Lodge Retreat",
    "City Center Suites",
    "Sunrise Beach Hotel",
    "Desert Oasis Inn",
    "Lakeside Paradise",
    "Garden Terrace Hotel",
    "Royal Palm Estate",
    "Skyline Business Hotel",
]

ROOM_TYPE_SPECS = [
    {"slug": "standard", "name": "Habitación Standard", "base_capacity": 2, "max_adults": 2, "max_children": 1, "inventory_total": 15},
    {"slug": "deluxe", "name": "Habitación Deluxe", "base_capacity": 3, "max_adults": 3, "max_children": 2, "inventory_total": 10},
    {"slug": "suite", "name": "Suite", "base_capacity": 4, "max_adults": 4, "max_children": 2, "inventory_total": 5},
]

RATE_PLAN_SPECS = [
    {"slug": "flex", "name": "Tarifa Flexible", "base_rate": 129.0, "delta": 5.0},
    {"slug": "advance", "name": "Tarifa Anticipada", "base_rate": 109.0, "delta": 3.0},
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_date(days_from_today: int) -> str:
    return (date.today() + timedelta(days=days_from_today)).isoformat()


def seed_hotels(db) -> list[int]:
    prop_ids = []
    for i in range(1, NUM_HOTELS + 1):
        name = HOTEL_NAMES[i - 1]
        prop_ids.append(i)
        db.dim_hotels.update_one(
            {"prop_id": i},
            {
                "$set": {
                    "prop_id": i,
                    "hotel_name": name,
                    "display_name": name,
                    "hotel_rating": 3.5 + (i * 0.15),
                    "prop_starrating": min(round(3 + (i * 0.2), 1), 5.0),
                    "prop_review_score": min(round(3.5 + (i * 0.12), 1), 5.0),
                    "active": True,
                    "demo_seed": True,
                    "source": SEED_SOURCE,
                    "updated_at": utc_now(),
                },
                "$setOnInsert": {"created_at": utc_now()},
            },
            upsert=True,
        )
    return prop_ids


def seed_room_types(db, prop_id: int) -> list[dict]:
    results = []
    for spec in ROOM_TYPE_SPECS:
        room_type_id = f"RT-{prop_id}-{spec['slug']}"
        # Preserve existing floor if present; default to "1" for new records
        existing = db.room_types.find_one({"room_type_id": room_type_id}, {"floor": 1})
        floor_val = (existing or {}).get("floor", "1")
        payload = {
            "room_type_id": room_type_id,
            "prop_id": prop_id,
            "name": spec["name"],
            "description": f"{spec['name']} - vista disponible",
            "base_capacity": spec["base_capacity"],
            "max_adults": spec["max_adults"],
            "max_children": spec["max_children"],
            "floor": floor_val,
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
        results.append({"room_type_id": room_type_id, "name": spec["name"], "total": spec["inventory_total"]})
    return results


def seed_inventory(db, prop_id: int, room_type_infos: list[dict]) -> int:
    """Seed inventory for FORECAST_DAYS starting from today."""
    count = 0
    for rt in room_type_infos:
        room_type_id = rt["room_type_id"]
        total = rt["total"]
        for day_offset in range(FORECAST_DAYS):
            d = iso_date(day_offset)
            # Simple occupancy simulation: weekends busier
            blocked = 2 if day_offset % 7 in (5, 6) else 0
            available = max(total - blocked - (day_offset % 3), 0)
            db.room_inventory_calendar.update_one(
                {"prop_id": prop_id, "room_type_id": room_type_id, "date": d},
                {
                    "$set": {
                        "prop_id": prop_id,
                        "room_type_id": room_type_id,
                        "date": d,
                        "total_rooms": total,
                        "available_rooms": available,
                        "blocked_rooms": blocked,
                        "demo_seed": True,
                        "source": SEED_SOURCE,
                        "updated_at": utc_now(),
                    },
                    "$setOnInsert": {"created_at": utc_now()},
                },
                upsert=True,
            )
            count += 1
    return count


def seed_rate_plans(db, prop_id: int) -> list[dict]:
    results = []
    for spec in RATE_PLAN_SPECS:
        rate_plan_id = f"RP-{prop_id}-{spec['slug']}"
        payload = {
            "rate_plan_id": rate_plan_id,
            "prop_id": prop_id,
            "name": spec["name"],
            "description": f"{spec['name']} - precio dinámico",
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
        results.append({"rate_plan_id": rate_plan_id, "base_rate": spec["base_rate"]})
    return results


def seed_rate_calendar(db, prop_id: int, rate_plans: list[dict]) -> int:
    count = 0
    for rp in rate_plans:
        rate_plan_id = rp["rate_plan_id"]
        base = rp["base_rate"]
        for day_offset in range(FORECAST_DAYS):
            d = iso_date(day_offset)
            amount = round(base + (day_offset * 1.5), 2)
            db.hotel_rate_calendar.update_one(
                {"prop_id": prop_id, "rate_plan_id": rate_plan_id, "date": d},
                {
                    "$set": {
                        "prop_id": prop_id,
                        "rate_plan_id": rate_plan_id,
                        "date": d,
                        "rate_amount": amount,
                        "currency": "USD",
                        "min_stay_nights": 1,
                        "is_closed": False,
                        "demo_seed": True,
                        "source": SEED_SOURCE,
                        "updated_at": utc_now(),
                    },
                    "$setOnInsert": {"created_at": utc_now()},
                },
                upsert=True,
            )
            count += 1
    return count


def seed_hotel_policies(db, prop_id: int) -> None:
    db.hotel_policies.update_one(
        {"prop_id": prop_id},
        {
            "$set": {
                "prop_id": prop_id,
                "check_in_time": "15:00",
                "check_out_time": "12:00",
                "cancellation_policy": "Cancelación gratuita hasta 24 horas antes de la llegada.",
                "pet_policy": "No se permiten mascotas.",
                "children_policy": "Niños menores de 12 años gratis compartiendo con adultos.",
                "payment_policy": "Se requiere tarjeta de crédito para garantizar la reserva.",
                "demo_seed": True,
                "source": SEED_SOURCE,
                "updated_at": utc_now(),
            },
            "$setOnInsert": {"created_at": utc_now()},
        },
        upsert=True,
    )


def seed_hotel_content(db, prop_id: int, hotel_name: str) -> None:
    db.hotel_content_pages.update_one(
        {"prop_id": prop_id},
        {
            "$set": {
                "prop_id": prop_id,
                "description": f"{hotel_name} te ofrece una estancia inolvidable con habitaciones cómodas y servicio de primera clase.",
                "highlights": "Ubicación privilegiada\\nAtención 24/7\\nWi-Fi gratuito",
                "amenities_text": "Wi-Fi, Desayuno, Piscina, Gimnasio, Estacionamiento, Aire acondicionado",
                "active_amenities": ["Wi-Fi", "Desayuno incluido", "Piscina", "Gimnasio", "Estacionamiento"],
                "amenities_catalog": [
                    {"category": "General", "label": "Wi-Fi"},
                    {"category": "Gastronomía", "label": "Desayuno incluido"},
                    {"category": "Bienestar", "label": "Piscina"},
                    {"category": "Bienestar", "label": "Gimnasio"},
                    {"category": "Servicios", "label": "Estacionamiento"},
                ],
                "demo_seed": True,
                "source": SEED_SOURCE,
                "updated_at": utc_now(),
            },
            "$setOnInsert": {"created_at": utc_now()},
        },
        upsert=True,
    )


def main() -> int:
    db = get_database()
    create_indexes(db)

    before = {
        "dim_hotels": db.dim_hotels.count_documents({}),
        "room_types": db.room_types.count_documents({}),
        "room_inventory_calendar": db.room_inventory_calendar.count_documents({}),
        "rate_plans": db.rate_plans.count_documents({}),
        "hotel_rate_calendar": db.hotel_rate_calendar.count_documents({}),
        "hotel_policies": db.hotel_policies.count_documents({}),
        "hotel_content_pages": db.hotel_content_pages.count_documents({}),
    }

    print(f"Before: {json.dumps(before, indent=2)}")

    prop_ids = seed_hotels(db)
    print(f"Seeded {len(prop_ids)} hotels")

    total_rt = 0
    total_inv = 0
    total_rp = 0
    total_rc = 0

    for pid in prop_ids:
        rt_infos = seed_room_types(db, pid)
        total_rt += len(rt_infos)
        inv_count = seed_inventory(db, pid, rt_infos)
        total_inv += inv_count
        rp_infos = seed_rate_plans(db, pid)
        total_rp += len(rp_infos)
        rc_count = seed_rate_calendar(db, pid, rp_infos)
        total_rc += rc_count
        seed_hotel_policies(db, pid)
        hotel_name = HOTEL_NAMES[pid - 1]
        seed_hotel_content(db, pid, hotel_name)
        print(f"  Hotel {pid} ({hotel_name}): {len(rt_infos)} room types, {inv_count} inventory days, {len(rp_infos)} rate plans, {rc_count} rate calendar days")

    after = {
        "dim_hotels": db.dim_hotels.count_documents({}),
        "room_types": db.room_types.count_documents({}),
        "room_inventory_calendar": db.room_inventory_calendar.count_documents({}),
        "rate_plans": db.rate_plans.count_documents({}),
        "hotel_rate_calendar": db.hotel_rate_calendar.count_documents({}),
        "hotel_policies": db.hotel_policies.count_documents({}),
        "hotel_content_pages": db.hotel_content_pages.count_documents({}),
    }

    delta = {k: after[k] - before[k] for k in before}

    report = {
        "script": SEED_SOURCE,
        "generated_at": utc_now().isoformat(),
        "before": before,
        "after": after,
        "delta": delta,
        "prop_ids": prop_ids,
        "forecast_days": FORECAST_DAYS,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")

    print("\nSeed completed:")
    print(json.dumps(delta, indent=2))
    print(f"Report saved to: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
