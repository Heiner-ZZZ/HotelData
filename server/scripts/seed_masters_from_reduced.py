import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from pymongo import UpdateOne
from pymongo.errors import BulkWriteError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database.connection import get_database

INPUT_CSV = Path(r"C:\HotelData\hoteldata_project\data\raw\hotels.csv")
CHUNK_SIZE = 100_000


def create_master_indexes(db):
    db.dim_hotels.create_index("prop_id", unique=True)
    db.dim_destinations.create_index("srch_destination_id", unique=True)
    db.dim_visitor_countries.create_index("visitor_location_country_id", unique=True)
    db.dim_dates.create_index("date_key", unique=True)

    db.dim_promotions.create_index("promotion_flag", unique=True)
    db.dim_reservation_status.create_index("reserva_bool", unique=True)
    db.dim_stay_length_category.create_index("stay_length_category_id", unique=True)
    db.dim_booking_window_category.create_index("booking_window_category_id", unique=True)
    db.dim_price_category.create_index("price_category_id", unique=True)

    db.fact_hotel_events.create_index("srch_id")
    db.fact_hotel_events.create_index("prop_id")
    db.fact_hotel_events.create_index("srch_destination_id")
    db.fact_hotel_events.create_index("visitor_location_country_id")
    db.fact_hotel_events.create_index("date_key")

    print("Indices creados correctamente.")


def seed_fixed_catalogs(db):
    now = datetime.now(timezone.utc)

    promotions = [
        {
            "promotion_flag": 0,
            "promotion_name": "Precio normal",
            "description": "El hotel no se encontraba en promocion.",
            "active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "promotion_flag": 1,
            "promotion_name": "En promocion",
            "description": "El hotel se encontraba en promocion u oferta.",
            "active": True,
            "created_at": now,
            "updated_at": now,
        },
    ]

    reservation_status = [
        {
            "reserva_bool": 0,
            "status_name": "Abandono",
            "description": "El usuario consulto o interactuo, pero no completo reserva.",
            "active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "reserva_bool": 1,
            "status_name": "Reserva completada",
            "description": "El usuario completo una reserva.",
            "active": True,
            "created_at": now,
            "updated_at": now,
        },
    ]

    stay_categories = [
        {
            "stay_length_category_id": "SHORT_STAY",
            "min_nights": 1,
            "max_nights": 2,
            "category_name": "Estancia corta",
            "description": "Reservas de 1 a 2 noches.",
            "active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "stay_length_category_id": "MEDIUM_STAY",
            "min_nights": 3,
            "max_nights": 7,
            "category_name": "Estancia media",
            "description": "Reservas de 3 a 7 noches.",
            "active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "stay_length_category_id": "LONG_STAY",
            "min_nights": 8,
            "max_nights": None,
            "category_name": "Estancia larga",
            "description": "Reservas de 8 noches o mas.",
            "active": True,
            "created_at": now,
            "updated_at": now,
        },
    ]

    booking_window_categories = [
        {
            "booking_window_category_id": "LAST_MINUTE",
            "min_days": 0,
            "max_days": 3,
            "category_name": "Ultimo minuto",
            "description": "Reserva realizada entre 0 y 3 dias antes.",
            "active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "booking_window_category_id": "SHORT_TERM",
            "min_days": 4,
            "max_days": 14,
            "category_name": "Corto plazo",
            "description": "Reserva realizada entre 4 y 14 dias antes.",
            "active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "booking_window_category_id": "MEDIUM_TERM",
            "min_days": 15,
            "max_days": 30,
            "category_name": "Mediano plazo",
            "description": "Reserva realizada entre 15 y 30 dias antes.",
            "active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "booking_window_category_id": "LONG_TERM",
            "min_days": 31,
            "max_days": None,
            "category_name": "Largo plazo",
            "description": "Reserva realizada con 31 dias o mas de anticipacion.",
            "active": True,
            "created_at": now,
            "updated_at": now,
        },
    ]

    price_categories = [
        {
            "price_category_id": "LOW_PRICE",
            "min_price": 0,
            "max_price": 75,
            "category_name": "Precio bajo",
            "description": "Hoteles con precio mostrado hasta 75 USD.",
            "active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "price_category_id": "MEDIUM_PRICE",
            "min_price": 75.01,
            "max_price": 150,
            "category_name": "Precio medio",
            "description": "Hoteles con precio mostrado entre 75.01 y 150 USD.",
            "active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "price_category_id": "HIGH_PRICE",
            "min_price": 150.01,
            "max_price": 300,
            "category_name": "Precio alto",
            "description": "Hoteles con precio mostrado entre 150.01 y 300 USD.",
            "active": True,
            "created_at": now,
            "updated_at": now,
        },
        {
            "price_category_id": "PREMIUM_PRICE",
            "min_price": 300.01,
            "max_price": None,
            "category_name": "Precio premium",
            "description": "Hoteles con precio mostrado superior a 300 USD.",
            "active": True,
            "created_at": now,
            "updated_at": now,
        },
    ]

    upsert_many(db.dim_promotions, "promotion_flag", promotions)
    upsert_many(db.dim_reservation_status, "reserva_bool", reservation_status)
    upsert_many(db.dim_stay_length_category, "stay_length_category_id", stay_categories)
    upsert_many(db.dim_booking_window_category, "booking_window_category_id", booking_window_categories)
    upsert_many(db.dim_price_category, "price_category_id", price_categories)

    print("Maestras fijas insertadas/actualizadas correctamente.")


def upsert_many(collection, key_field, docs):
    if not docs:
        return

    operations = []
    now = datetime.now(timezone.utc)

    for doc in docs:
        key_value = doc.get(key_field)

        if key_value is None or pd.isna(key_value):
            continue

        insert_doc = {key: value for key, value in doc.items() if key != "updated_at"}

        operations.append(
            UpdateOne(
                {key_field: key_value},
                {
                    "$setOnInsert": insert_doc,
                    "$set": {"updated_at": now},
                },
                upsert=True,
            )
        )

    if operations:
        try:
            collection.bulk_write(operations, ordered=False)
        except BulkWriteError as exc:
            print(f"Advertencia en bulk_write para {collection.name}: {exc.details}")


def seed_dynamic_masters_from_csv(db):
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"No existe el archivo: {INPUT_CSV}")

    required_columns = [
        "prop_id",
        "srch_destination_id",
        "visitor_location_country_id",
        "date_time",
    ]

    header = pd.read_csv(INPUT_CSV, nrows=0)
    missing = [col for col in required_columns if col not in header.columns]

    if missing:
        raise ValueError(f"Faltan columnas necesarias para maestras: {missing}")

    total_rows = 0

    for chunk in pd.read_csv(INPUT_CSV, chunksize=CHUNK_SIZE):
        total_rows += len(chunk)

        now = datetime.now(timezone.utc)

        hotel_docs = []
        for prop_id in chunk["prop_id"].dropna().unique():
            hotel_docs.append(
                {
                    "prop_id": int(prop_id),
                    "hotel_name": f"Hotel {int(prop_id)}",
                    "hotel_rating": None,
                    "description": "Hotel generado desde identificador prop_id del dataset transaccional.",
                    "active": True,
                    "created_at": now,
                    "updated_at": now,
                }
            )

        destination_docs = []
        for destination_id in chunk["srch_destination_id"].dropna().unique():
            destination_docs.append(
                {
                    "srch_destination_id": int(destination_id),
                    "destination_name": f"Destino {int(destination_id)}",
                    "description": "Destino generado desde identificador srch_destination_id del dataset transaccional.",
                    "active": True,
                    "created_at": now,
                    "updated_at": now,
                }
            )

        country_docs = []
        for country_id in chunk["visitor_location_country_id"].dropna().unique():
            country_docs.append(
                {
                    "visitor_location_country_id": int(country_id),
                    "country_name": f"Pais {int(country_id)}",
                    "description": "Pais de origen del visitante generado desde visitor_location_country_id.",
                    "active": True,
                    "created_at": now,
                    "updated_at": now,
                }
            )

        dates = pd.to_datetime(chunk["date_time"], errors="coerce").dropna()
        date_docs = []

        for date_time in dates.drop_duplicates():
            date_key = int(date_time.strftime("%Y%m%d%H"))

            date_docs.append(
                {
                    "date_key": date_key,
                    "full_date": date_time.to_pydatetime(),
                    "year": int(date_time.year),
                    "month": int(date_time.month),
                    "day": int(date_time.day),
                    "hour": int(date_time.hour),
                    "created_at": now,
                    "updated_at": now,
                }
            )

        upsert_many(db.dim_hotels, "prop_id", hotel_docs)
        upsert_many(db.dim_destinations, "srch_destination_id", destination_docs)
        upsert_many(db.dim_visitor_countries, "visitor_location_country_id", country_docs)
        upsert_many(db.dim_dates, "date_key", date_docs)

        print(f"Filas analizadas para maestras: {total_rows}")

    print("Maestras dinamicas desde CSV insertadas/actualizadas correctamente.")


def print_summary(db):
    collections = [
        "dim_hotels",
        "dim_destinations",
        "dim_visitor_countries",
        "dim_dates",
        "dim_promotions",
        "dim_reservation_status",
        "dim_stay_length_category",
        "dim_booking_window_category",
        "dim_price_category",
    ]

    print("\nResumen de colecciones maestras:")
    for name in collections:
        count = db[name].count_documents({})
        print(f"- {name}: {count} documentos")


def main():
    print("Conectando a MongoDB...")
    db = get_database()

    print("Creando indices...")
    create_master_indexes(db)

    print("Insertando maestras fijas...")
    seed_fixed_catalogs(db)

    print("Insertando maestras dinamicas desde CSV...")
    seed_dynamic_masters_from_csv(db)

    print_summary(db)

    print("\nSeed de colecciones maestras finalizado correctamente.")


if __name__ == "__main__":
    main()
