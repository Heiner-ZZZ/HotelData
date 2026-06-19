from __future__ import annotations

import json
from datetime import datetime, timezone

import pandas as pd

from config.settings import get_settings
from src.etl.schema import FACT_OPTIONAL_COLUMNS, FACT_REQUIRED_COLUMNS


FACT_COLUMNS = [
    "srch_id",
    "date_time",
    "date_key",
    "prop_id",
    "srch_destination_id",
    "visitor_location_country_id",
    "promotion_flag",
    "reserva_bool",
    "occupancy_profile_id",
    "stay_length_category_id",
    "booking_window_category_id",
    "price_category_id",
    "price_usd",
    "reservas_brutas_usd",
    "srch_length_of_stay",
    "srch_booking_window",
    "srch_adults_count",
    "srch_children_count",
    "srch_room_count",
    "loaded_at",
    "execution_id",
]


def _clean_int(value) -> int | None:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    try:
        return int(float(str(value).strip()))
    except ValueError:
        return None


def _clean_float(value) -> float | None:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def _reservation_status(row) -> int:
    reserva_bool = _clean_int(row.get("reserva_bool"))
    if reserva_bool is not None:
        return 1 if reserva_bool == 1 else 0
    booking_bool = _clean_int(row.get("booking_bool"))
    if booking_bool is not None:
        return 1 if booking_bool == 1 else 0
    return 0


def _date_key(value) -> tuple[str | None, int | None]:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return None, None
    return parsed.isoformat(), int(parsed.strftime("%Y%m%d%H"))


def _stay_length_category_id(nights: int | None) -> str | None:
    if nights is None:
        return None
    if nights <= 2:
        return "SHORT_STAY"
    if nights <= 7:
        return "MEDIUM_STAY"
    return "LONG_STAY"


def _booking_window_category_id(days: int | None) -> str | None:
    if days is None:
        return None
    if days <= 3:
        return "LAST_MINUTE"
    if days <= 14:
        return "SHORT_TERM"
    if days <= 30:
        return "MEDIUM_TERM"
    return "LONG_TERM"


def _price_category_id(price: float | None) -> str | None:
    if price is None:
        return None
    if price < 100:
        return "LOW_PRICE"
    if price < 250:
        return "MEDIUM_PRICE"
    if price < 500:
        return "HIGH_PRICE"
    return "PREMIUM_PRICE"


def _occupancy_profile_id(adults: int | None, children: int | None, rooms: int | None) -> str | None:
    if adults is None or children is None or rooms is None:
        return None
    return f"A{adults}_C{children}_R{rooms}"


def _append_jsonl(path, documents: list[dict]) -> int:
    if not documents:
        return 0
    with path.open("a", encoding="utf-8") as target:
        for document in documents:
            target.write(json.dumps(document, ensure_ascii=False) + "\n")
    return len(documents)


def _execution_id() -> str:
    settings = get_settings()
    marker = settings.staging_dir / "execution_id.txt"
    if marker.exists():
        return marker.read_text(encoding="utf-8").strip()
    value = f"etl_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    marker.write_text(value, encoding="utf-8")
    return value


def transform_fact_events() -> dict:
    settings = get_settings()
    staging_path = settings.staging_dir / "hotels_extracted.jsonl"
    candidate_path = settings.processed_dir / "fact_hotel_events_candidate.jsonl"
    rejected_path = settings.processed_dir / "rejected_records_transform.jsonl"
    for path in [candidate_path, rejected_path]:
        if path.exists():
            path.unlink()

    execution_id = _execution_id()
    loaded_at = datetime.now(timezone.utc).isoformat()
    transformed = 0
    rejected = 0

    for chunk in pd.read_json(staging_path, lines=True, dtype=False, chunksize=settings.chunk_size):
        for column in FACT_OPTIONAL_COLUMNS:
            if column not in chunk.columns:
                chunk[column] = None
        valid_docs = []
        rejected_docs = []
        for _, row in chunk.iterrows():
            iso_date, date_key = _date_key(row.get("date_time"))
            reserva_bool = _reservation_status(row)
            price_usd = _clean_float(row.get("price_usd"))
            gross_bookings_usd = _clean_float(row.get("gross_bookings_usd"))
            promotion_flag = _clean_int(row.get("promotion_flag"))
            if promotion_flag is None:
                promotion_flag = 0
            length_of_stay = _clean_int(row.get("srch_length_of_stay"))
            booking_window = _clean_int(row.get("srch_booking_window"))
            adults_count = _clean_int(row.get("srch_adults_count"))
            children_count = _clean_int(row.get("srch_children_count"))
            room_count = _clean_int(row.get("srch_room_count"))
            document = {
                "srch_id": _clean_int(row.get("srch_id")),
                "date_time": iso_date,
                "date_key": date_key,
                "prop_id": _clean_int(row.get("prop_id")),
                "srch_destination_id": _clean_int(row.get("srch_destination_id")),
                "visitor_location_country_id": _clean_int(row.get("visitor_location_country_id")),
                "promotion_flag": promotion_flag,
                "reserva_bool": reserva_bool,
                "occupancy_profile_id": _occupancy_profile_id(adults_count, children_count, room_count),
                "stay_length_category_id": _stay_length_category_id(length_of_stay),
                "booking_window_category_id": _booking_window_category_id(booking_window),
                "price_category_id": _price_category_id(price_usd),
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
            missing = [column for column in FACT_REQUIRED_COLUMNS + ["date_key"] if document.get(column) is None]
            if missing:
                rejected_docs.append({
                    "reason": "invalid_required_fields",
                    "missing_fields": missing,
                    "raw_record": row.to_dict(),
                    "loaded_at": loaded_at,
                    "execution_id": execution_id,
                })
            else:
                valid_docs.append({key: document.get(key) for key in FACT_COLUMNS})
        transformed += _append_jsonl(candidate_path, valid_docs)
        rejected += _append_jsonl(rejected_path, rejected_docs)

    return {
        "execution_id": execution_id,
        "candidate_path": str(candidate_path),
        "transform_rejected_path": str(rejected_path),
        "candidate_records": transformed,
        "transform_rejected_records": rejected,
    }
