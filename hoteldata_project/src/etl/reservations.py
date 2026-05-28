from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from config.settings import get_settings
from src.etl.parquet_io import read_reservations_parquet
from src.etl.transform_fact import (
    FACT_COLUMNS,
    _booking_window_category_id,
    _clean_float,
    _clean_int,
    _date_key,
    _execution_id,
    _occupancy_profile_id,
    _price_category_id,
    _reservation_status,
    _stay_length_category_id,
)


DIMENSION_COLLECTIONS = [
    "dim_hotels",
    "dim_destinations",
    "dim_visitor_countries",
    "dim_dates",
    "dim_promotions",
    "dim_reservation_status",
    "dim_stay_length_category",
    "dim_booking_window_category",
    "dim_price_category",
    "dim_occupancy_profile",
]


def _write_jsonl(path: Path, documents: list[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as sink:
        for document in documents:
            sink.write(json.dumps(document, ensure_ascii=False) + "\n")
    return len(documents)


def _append_jsonl(path: Path, documents: list[dict[str, Any]]) -> int:
    if not documents:
        return 0
    with path.open("a", encoding="utf-8") as sink:
        for document in documents:
            sink.write(json.dumps(document, ensure_ascii=False) + "\n")
    return len(documents)


def _label(prefix: str, value: int | str | None) -> str:
    return f"{prefix} {value}" if value is not None else f"{prefix} desconocido"


def transform_reservations_from_parquet() -> dict:
    settings = get_settings()
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    dataframe = read_reservations_parquet()
    execution_id = _execution_id()
    loaded_at = datetime.now(timezone.utc).isoformat()

    fact_path = settings.processed_dir / "fact_hotel_reservations.jsonl"
    rejected_path = settings.processed_dir / "rejected_records_transform.jsonl"
    for path in [fact_path, rejected_path]:
        if path.exists():
            path.unlink()

    dimensions: dict[str, dict[Any, dict[str, Any]]] = {name: {} for name in DIMENSION_COLLECTIONS}
    fact_count = 0
    rejected_count = 0

    for _, row in dataframe.iterrows():
        iso_date, date_key = _date_key(row.get("date_time"))
        reserva_bool = _reservation_status(row)
        price_usd = _clean_float(row.get("price_usd"))
        gross_bookings_usd = _clean_float(row.get("gross_bookings_usd"))
        promotion_flag = _clean_int(row.get("promotion_flag"))
        promotion_flag = 0 if promotion_flag is None else promotion_flag
        length_of_stay = _clean_int(row.get("srch_length_of_stay"))
        booking_window = _clean_int(row.get("srch_booking_window"))
        adults_count = _clean_int(row.get("srch_adults_count"))
        children_count = _clean_int(row.get("srch_children_count"))
        room_count = _clean_int(row.get("srch_room_count"))
        prop_id = _clean_int(row.get("prop_id"))
        destination_id = _clean_int(row.get("srch_destination_id"))
        country_id = _clean_int(row.get("visitor_location_country_id"))
        stay_category = _stay_length_category_id(length_of_stay)
        booking_category = _booking_window_category_id(booking_window)
        price_category = _price_category_id(price_usd)
        occupancy_profile = _occupancy_profile_id(adults_count, children_count, room_count)

        document = {
            "srch_id": _clean_int(row.get("srch_id")),
            "date_time": iso_date,
            "date_key": date_key,
            "prop_id": prop_id,
            "srch_destination_id": destination_id,
            "visitor_location_country_id": country_id,
            "promotion_flag": promotion_flag,
            "reserva_bool": reserva_bool,
            "occupancy_profile_id": occupancy_profile,
            "stay_length_category_id": stay_category,
            "booking_window_category_id": booking_category,
            "price_category_id": price_category,
            "price_usd": price_usd,
            "reservas_brutas_usd": (
                gross_bookings_usd
                if gross_bookings_usd is not None
                else price_usd if reserva_bool == 1 and price_usd is not None else 0
            ),
            "srch_length_of_stay": length_of_stay,
            "srch_booking_window": booking_window,
            "srch_adults_count": adults_count,
            "srch_children_count": children_count,
            "srch_room_count": room_count,
            "loaded_at": loaded_at,
            "execution_id": execution_id,
        }
        missing = [
            field
            for field in ["srch_id", "date_key", "prop_id", "srch_destination_id", "visitor_location_country_id", "price_usd"]
            if document.get(field) is None
        ]
        if missing:
            rejected_count += _append_jsonl(
                rejected_path,
                [{"reason": "invalid_required_fields", "missing_fields": missing, "raw_record": row.to_dict(), "loaded_at": loaded_at, "execution_id": execution_id}],
            )
            continue

        dimensions["dim_hotels"][prop_id] = {
            "prop_id": prop_id,
            "hotel_name": row.get("hotel_name") or row.get("prop_name") or _label("Hotel", prop_id),
            "hotel_rating": _clean_float(row.get("hotel_rating")),
            "loaded_at": loaded_at,
        }
        dimensions["dim_destinations"][destination_id] = {
            "srch_destination_id": destination_id,
            "destination_name": row.get("destination_name") or _label("Destino", destination_id),
            "loaded_at": loaded_at,
        }
        dimensions["dim_visitor_countries"][country_id] = {
            "visitor_location_country_id": country_id,
            "country_name": row.get("country_name") or _label("Pais", country_id),
            "loaded_at": loaded_at,
        }
        if date_key is not None:
            parsed = pd.to_datetime(iso_date)
            dimensions["dim_dates"][date_key] = {
                "date_key": date_key,
                "date_time": iso_date,
                "year": int(parsed.year),
                "month": int(parsed.month),
                "day": int(parsed.day),
                "hour": int(parsed.hour),
                "loaded_at": loaded_at,
            }
        dimensions["dim_promotions"][promotion_flag] = {
            "promotion_flag": promotion_flag,
            "promotion_label": "Promocion" if promotion_flag == 1 else "Sin promocion",
        }
        dimensions["dim_reservation_status"][reserva_bool] = {
            "reserva_bool": reserva_bool,
            "reservation_status": "Reservada" if reserva_bool == 1 else "No reservada",
        }
        if stay_category:
            dimensions["dim_stay_length_category"][stay_category] = {
                "stay_length_category_id": stay_category,
                "stay_length_category": stay_category.replace("_", " ").title(),
            }
        if booking_category:
            dimensions["dim_booking_window_category"][booking_category] = {
                "booking_window_category_id": booking_category,
                "booking_window_category": booking_category.replace("_", " ").title(),
            }
        if price_category:
            dimensions["dim_price_category"][price_category] = {
                "price_category_id": price_category,
                "price_category": price_category.replace("_", " ").title(),
            }
        if occupancy_profile:
            dimensions["dim_occupancy_profile"][occupancy_profile] = {
                "occupancy_profile_id": occupancy_profile,
                "adults_count": adults_count,
                "children_count": children_count,
                "room_count": room_count,
            }

        fact_count += _append_jsonl(fact_path, [{key: document.get(key) for key in FACT_COLUMNS}])

    dimension_counts = {}
    for collection_name, documents_by_key in dimensions.items():
        dimension_counts[collection_name] = _write_jsonl(
            settings.processed_dir / f"{collection_name}.jsonl",
            list(documents_by_key.values()),
        )

    return {
        "execution_id": execution_id,
        "fact_path": str(fact_path),
        "fact_records": fact_count,
        "rejected_records": rejected_count,
        "dimensions": dimension_counts,
    }
