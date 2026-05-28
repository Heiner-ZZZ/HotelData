from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

import pandas as pd


REQUIRED_FACT_COLUMNS = [
    "srch_id",
    "date_time",
    "site_id",
    "visitor_location_country_id",
    "prop_country_id",
    "prop_id",
    "price_usd",
    "promotion_flag",
    "srch_destination_id",
    "srch_length_of_stay",
    "srch_booking_window",
    "srch_adults_count",
    "srch_children_count",
    "srch_room_count",
    "click_bool",
    "reserva_bool",
    "reservas_brutas_usd",
]


FACT_COLUMNS = [
    "source_record_id",
    "srch_id",
    "date_time",
    "date_key",
    "site_id",
    "visitor_location_country_id",
    "visitor_hist_starrating",
    "visitor_hist_adr_usd",
    "prop_country_id",
    "prop_id",
    "prop_starrating",
    "prop_review_score",
    "prop_brand_bool",
    "prop_location_score1",
    "price_usd",
    "promotion_flag",
    "srch_destination_id",
    "srch_length_of_stay",
    "srch_booking_window",
    "srch_adults_count",
    "srch_children_count",
    "srch_room_count",
    "click_bool",
    "reserva_bool",
    "reservas_brutas_usd",
    "occupancy_profile_id",
    "stay_length_category_id",
    "booking_window_category_id",
    "price_category_id",
    "loaded_at",
    "execution_id",
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_native(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def clean_int(value: Any) -> int | None:
    value = to_native(value)
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def clean_float(value: Any) -> float | None:
    value = to_native(value)
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def clean_bool(value: Any) -> bool | None:
    value = to_native(value)
    if value is None or str(value).strip() == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "si"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
    number = clean_int(value)
    if number is None:
        return None
    return number == 1


def parse_date(value: Any) -> tuple[str | None, int | None]:
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    if pd.isna(parsed):
        return None, None
    return parsed.isoformat(), int(parsed.strftime("%Y%m%d"))


def stay_length_category_id(nights: int | None) -> str | None:
    if nights is None:
        return None
    if nights <= 2:
        return "SHORT_STAY"
    if nights <= 7:
        return "MEDIUM_STAY"
    return "LONG_STAY"


def booking_window_category_id(days: int | None) -> str | None:
    if days is None:
        return None
    if days <= 3:
        return "LAST_MINUTE"
    if days <= 14:
        return "SHORT_TERM"
    if days <= 30:
        return "MEDIUM_TERM"
    return "LONG_TERM"


def price_category_id(price: float | None) -> str | None:
    if price is None:
        return None
    if price < 100:
        return "LOW_PRICE"
    if price < 250:
        return "MEDIUM_PRICE"
    if price < 500:
        return "HIGH_PRICE"
    return "PREMIUM_PRICE"


def occupancy_profile_id(adults: int | None, children: int | None, rooms: int | None) -> str | None:
    if adults is None or children is None or rooms is None:
        return None
    return f"A{adults}_C{children}_R{rooms}"


def transform_fact_hotel_reservations(
    dataframe: pd.DataFrame,
    execution_id: str,
    loaded_at: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], pd.DataFrame]:
    loaded_at = loaded_at or utc_now_iso()
    facts: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    valid_rows: list[dict[str, Any]] = []

    missing_source_columns = [column for column in REQUIRED_FACT_COLUMNS if column not in dataframe.columns]
    if missing_source_columns:
        raise ValueError(f"Parquet sin columnas requeridas: {missing_source_columns}")

    for _, row in dataframe.iterrows():
        date_time, date_key = parse_date(row.get("date_time"))
        length_of_stay = clean_int(row.get("srch_length_of_stay"))
        booking_window = clean_int(row.get("srch_booking_window"))
        adults = clean_int(row.get("srch_adults_count"))
        children = clean_int(row.get("srch_children_count"))
        rooms = clean_int(row.get("srch_room_count"))
        price = clean_float(row.get("price_usd"))
        gross = clean_float(row.get("reservas_brutas_usd"))
        reserva_bool = clean_bool(row.get("reserva_bool"))
        click_bool = clean_bool(row.get("click_bool"))
        promotion_flag = clean_bool(row.get("promotion_flag"))
        prop_brand_bool = clean_bool(row.get("prop_brand_bool"))

        document = {
            "source_record_id": to_native(row.get("id")),
            "srch_id": clean_int(row.get("srch_id")),
            "date_time": date_time,
            "date_key": date_key,
            "site_id": clean_int(row.get("site_id")),
            "visitor_location_country_id": clean_int(row.get("visitor_location_country_id")),
            "visitor_hist_starrating": clean_float(row.get("visitor_hist_starrating")),
            "visitor_hist_adr_usd": clean_float(row.get("visitor_hist_adr_usd")),
            "prop_country_id": clean_int(row.get("prop_country_id")),
            "prop_id": clean_int(row.get("prop_id")),
            "prop_starrating": clean_int(row.get("prop_starrating")),
            "prop_review_score": clean_float(row.get("prop_review_score")),
            "prop_brand_bool": prop_brand_bool,
            "prop_location_score1": clean_float(row.get("prop_location_score1")),
            "price_usd": price,
            "promotion_flag": promotion_flag,
            "srch_destination_id": clean_int(row.get("srch_destination_id")),
            "srch_length_of_stay": length_of_stay,
            "srch_booking_window": booking_window,
            "srch_adults_count": adults,
            "srch_children_count": children,
            "srch_room_count": rooms,
            "click_bool": click_bool,
            "reserva_bool": reserva_bool,
            "reservas_brutas_usd": gross if gross is not None else (price if reserva_bool and price is not None else 0.0),
            "occupancy_profile_id": occupancy_profile_id(adults, children, rooms),
            "stay_length_category_id": stay_length_category_id(length_of_stay),
            "booking_window_category_id": booking_window_category_id(booking_window),
            "price_category_id": price_category_id(price),
            "loaded_at": loaded_at,
            "execution_id": execution_id,
        }

        missing = [
            field
            for field in [
                "srch_id",
                "date_key",
                "site_id",
                "visitor_location_country_id",
                "prop_id",
                "price_usd",
                "promotion_flag",
                "srch_destination_id",
                "click_bool",
                "reserva_bool",
            ]
            if document.get(field) is None
        ]
        invalid = []
        if document["price_usd"] is not None and document["price_usd"] < 0:
            invalid.append("negative_price_usd")
        if document["reservas_brutas_usd"] is not None and document["reservas_brutas_usd"] < 0:
            invalid.append("negative_reservas_brutas_usd")

        if missing or invalid:
            rejected.append(
                {
                    "reason": "invalid_fact_record",
                    "missing_fields": missing,
                    "invalid_fields": invalid,
                    "source_record_id": to_native(row.get("id")),
                    "raw_record": {key: to_native(value) for key, value in row.to_dict().items()},
                    "loaded_at": loaded_at,
                    "execution_id": execution_id,
                }
            )
            continue

        fact = {column: document.get(column) for column in FACT_COLUMNS}
        facts.append(fact)
        valid_rows.append(fact)

    return facts, rejected, pd.DataFrame(valid_rows)
