from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from pymongo import UpdateOne

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import get_settings
from src.database.connection import get_database
from src.database.indexes import create_indexes


MASTER_SEED_REQUIRED_COLUMNS = [
    "date_time",
    "prop_id",
    "srch_destination_id",
    "visitor_location_country_id",
]

MASTER_SEED_OPTIONAL_COLUMNS = [
    "srch_adults_count",
    "srch_children_count",
    "srch_room_count",
]


def _clean_int(value) -> int | None:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    try:
        return int(float(str(value).strip()))
    except ValueError:
        return None


def _date_document(value) -> dict | None:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None
    return {
        "date_key": int(parsed.strftime("%Y%m%d%H")),
        "full_date": parsed.isoformat(),
        "year": int(parsed.year),
        "month": int(parsed.month),
        "day": int(parsed.day),
        "hour": int(parsed.hour),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _occupancy_profile_id(adults: int | None, children: int | None, rooms: int | None) -> str | None:
    if adults is None or children is None or rooms is None:
        return None
    return f"A{adults}_C{children}_R{rooms}"


def _bulk_upsert(collection, operations: list[UpdateOne]) -> int:
    if not operations:
        return 0
    result = collection.bulk_write(operations, ordered=False)
    return result.upserted_count


def _seed_static_dimensions(db) -> dict[str, int]:
    static_docs = {
        "dim_promotions": [
            {
                "promotion_flag": 0,
                "promotion_name": "Precio normal",
                "description": "Evento sin promocion aplicada",
                "active": True,
            },
            {
                "promotion_flag": 1,
                "promotion_name": "En promocion",
                "description": "Evento con promocion aplicada",
                "active": True,
            },
        ],
        "dim_reservation_status": [
            {
                "reserva_bool": 0,
                "status_name": "Abandono / no reservo",
                "description": "Busqueda sin reserva completada",
                "active": True,
            },
            {
                "reserva_bool": 1,
                "status_name": "Reserva completada",
                "description": "Busqueda que termino en reserva",
                "active": True,
            },
        ],
        "dim_stay_length_category": [
            {
                "stay_length_category_id": "SHORT_STAY",
                "min_nights": 1,
                "max_nights": 2,
                "category_name": "SHORT_STAY",
                "description": "Estadia de 1 a 2 noches",
                "active": True,
            },
            {
                "stay_length_category_id": "MEDIUM_STAY",
                "min_nights": 3,
                "max_nights": 7,
                "category_name": "MEDIUM_STAY",
                "description": "Estadia de 3 a 7 noches",
                "active": True,
            },
            {
                "stay_length_category_id": "LONG_STAY",
                "min_nights": 8,
                "max_nights": None,
                "category_name": "LONG_STAY",
                "description": "Estadia de 8 o mas noches",
                "active": True,
            },
        ],
        "dim_booking_window_category": [
            {
                "booking_window_category_id": "LAST_MINUTE",
                "min_days": 0,
                "max_days": 3,
                "category_name": "LAST_MINUTE",
                "description": "Reserva con 0 a 3 dias de anticipacion",
                "active": True,
            },
            {
                "booking_window_category_id": "SHORT_TERM",
                "min_days": 4,
                "max_days": 14,
                "category_name": "SHORT_TERM",
                "description": "Reserva con 4 a 14 dias de anticipacion",
                "active": True,
            },
            {
                "booking_window_category_id": "MEDIUM_TERM",
                "min_days": 15,
                "max_days": 30,
                "category_name": "MEDIUM_TERM",
                "description": "Reserva con 15 a 30 dias de anticipacion",
                "active": True,
            },
            {
                "booking_window_category_id": "LONG_TERM",
                "min_days": 31,
                "max_days": None,
                "category_name": "LONG_TERM",
                "description": "Reserva con 31 o mas dias de anticipacion",
                "active": True,
            },
        ],
        "dim_price_category": [
            {
                "price_category_id": "LOW_PRICE",
                "min_price": 0,
                "max_price": 99.99,
                "category_name": "LOW_PRICE",
                "description": "Precio menor a 100 USD",
                "active": True,
            },
            {
                "price_category_id": "MEDIUM_PRICE",
                "min_price": 100,
                "max_price": 249.99,
                "category_name": "MEDIUM_PRICE",
                "description": "Precio entre 100 y 249.99 USD",
                "active": True,
            },
            {
                "price_category_id": "HIGH_PRICE",
                "min_price": 250,
                "max_price": 499.99,
                "category_name": "HIGH_PRICE",
                "description": "Precio entre 250 y 499.99 USD",
                "active": True,
            },
            {
                "price_category_id": "PREMIUM_PRICE",
                "min_price": 500,
                "max_price": None,
                "category_name": "PREMIUM_PRICE",
                "description": "Precio de 500 USD o mas",
                "active": True,
            },
        ],
    }
    keys = {
        "dim_promotions": "promotion_flag",
        "dim_reservation_status": "reserva_bool",
        "dim_stay_length_category": "stay_length_category_id",
        "dim_booking_window_category": "booking_window_category_id",
        "dim_price_category": "price_category_id",
    }
    inserted = {}
    for collection_name, documents in static_docs.items():
        key = keys[collection_name]
        operations = [
            UpdateOne({key: document[key]}, {"$setOnInsert": document}, upsert=True)
            for document in documents
        ]
        inserted[collection_name] = _bulk_upsert(db[collection_name], operations)
    return inserted


def main() -> None:
    settings = get_settings()
    if not settings.raw_csv_path.exists():
        raise FileNotFoundError(f"Expected raw CSV at {settings.raw_csv_path}")

    db = get_database()
    create_indexes(db)
    inserted = {
        "dim_hotels": 0,
        "dim_destinations": 0,
        "dim_visitor_countries": 0,
        "dim_dates": 0,
        "dim_occupancy_profile": 0,
    }
    inserted.update(_seed_static_dimensions(db))
    now = datetime.now(timezone.utc).isoformat()

    sample_columns = pd.read_csv(settings.raw_csv_path, nrows=0).columns.tolist()
    missing = [column for column in MASTER_SEED_REQUIRED_COLUMNS if column not in sample_columns]
    if missing:
        raise ValueError(f"Missing required transactional columns for master seed: {missing}")

    usecols = MASTER_SEED_REQUIRED_COLUMNS + [
        column for column in MASTER_SEED_OPTIONAL_COLUMNS if column in sample_columns
    ]

    for chunk in pd.read_csv(
        settings.raw_csv_path,
        dtype=str,
        keep_default_na=False,
        usecols=usecols,
        nrows=settings.demo_row_limit,
        chunksize=settings.chunk_size,
    ):
        hotel_ops = []
        destination_ops = []
        country_ops = []
        date_ops = []
        occupancy_ops = []

        for prop_id in {_clean_int(value) for value in chunk["prop_id"]}:
            if prop_id is not None:
                hotel_ops.append(
                    UpdateOne(
                        {"prop_id": prop_id},
                        {
                            "$setOnInsert": {
                                "prop_id": prop_id,
                                "hotel_name": "Hotel no especificado",
                                "hotel_rating": None,
                                "description": "Hotel creado desde semilla inicial de maestras",
                                "active": True,
                                "created_at": now,
                                "updated_at": now,
                            }
                        },
                        upsert=True,
                    )
                )

        for destination_id in {_clean_int(value) for value in chunk["srch_destination_id"]}:
            if destination_id is not None:
                destination_ops.append(
                    UpdateOne(
                        {"srch_destination_id": destination_id},
                        {
                            "$setOnInsert": {
                                "srch_destination_id": destination_id,
                                "destination_name": "Destino no especificado",
                                "description": "Destino creado desde semilla inicial de maestras",
                                "active": True,
                                "created_at": now,
                                "updated_at": now,
                            }
                        },
                        upsert=True,
                    )
                )

        for country_id in {_clean_int(value) for value in chunk["visitor_location_country_id"]}:
            if country_id is not None:
                country_ops.append(
                    UpdateOne(
                        {"visitor_location_country_id": country_id},
                        {
                            "$setOnInsert": {
                                "visitor_location_country_id": country_id,
                                "country_name": "Pais no especificado",
                                "description": "Pais creado desde semilla inicial de maestras",
                                "active": True,
                                "created_at": now,
                                "updated_at": now,
                            }
                        },
                        upsert=True,
                    )
                )

        seen_dates = {}
        for value in chunk["date_time"]:
            document = _date_document(value)
            if document is not None:
                seen_dates[document["date_key"]] = document
        for document in seen_dates.values():
            date_ops.append(UpdateOne({"date_key": document["date_key"]}, {"$setOnInsert": document}, upsert=True))

        if {"srch_adults_count", "srch_children_count", "srch_room_count"}.issubset(chunk.columns):
            profiles = set()
            for _, row in chunk.iterrows():
                adults = _clean_int(row.get("srch_adults_count"))
                children = _clean_int(row.get("srch_children_count"))
                rooms = _clean_int(row.get("srch_room_count"))
                profile_id = _occupancy_profile_id(adults, children, rooms)
                if profile_id is not None:
                    profiles.add((profile_id, adults, children, rooms))
            for profile_id, adults, children, rooms in profiles:
                occupancy_ops.append(
                    UpdateOne(
                        {"occupancy_profile_id": profile_id},
                        {
                            "$setOnInsert": {
                                "occupancy_profile_id": profile_id,
                                "adults_count": adults,
                                "children_count": children,
                                "room_count": rooms,
                                "profile_name": profile_id,
                                "description": "Perfil de ocupacion creado desde semilla inicial",
                                "active": True,
                            }
                        },
                        upsert=True,
                    )
                )

        inserted["dim_hotels"] += _bulk_upsert(db.dim_hotels, hotel_ops)
        inserted["dim_destinations"] += _bulk_upsert(db.dim_destinations, destination_ops)
        inserted["dim_visitor_countries"] += _bulk_upsert(db.dim_visitor_countries, country_ops)
        inserted["dim_dates"] += _bulk_upsert(db.dim_dates, date_ops)
        inserted["dim_occupancy_profile"] += _bulk_upsert(db.dim_occupancy_profile, occupancy_ops)

    print(f"Master seed completed: {inserted}")


if __name__ == "__main__":
    main()
