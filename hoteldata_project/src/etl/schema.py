from __future__ import annotations

LEGACY_HOTEL_COLUMNS = [
    "Address",
    "Attractions",
    "Description",
    "FaxNumber",
    "HotelCode",
    "HotelFacilities",
    "HotelName",
    "HotelRating",
    "HotelWebsiteUrl",
    "Map",
    "PhoneNumber",
    "PinCode",
    "cityCode",
    "cityName",
    "countyName",
    "countyCode",
]

FACT_REQUIRED_COLUMNS = [
    "srch_id",
    "date_time",
    "prop_id",
    "srch_destination_id",
    "visitor_location_country_id",
    "price_usd",
]

FACT_OPTIONAL_COLUMNS = [
    "reserva_bool",
    "booking_bool",
    "promotion_flag",
    "gross_bookings_usd",
    "srch_length_of_stay",
    "srch_booking_window",
    "srch_adults_count",
    "srch_children_count",
    "srch_room_count",
]

EXPECTED_COLUMNS = FACT_REQUIRED_COLUMNS


def validate_columns(columns: list[str], expected_columns: list[str] | None = None) -> dict:
    expected = expected_columns or EXPECTED_COLUMNS
    missing = [column for column in expected if column not in columns]
    unexpected = [column for column in columns if column not in expected]
    return {
        "valid": not missing,
        "expected_columns": expected,
        "missing_columns": missing,
        "unexpected_columns": unexpected,
    }
