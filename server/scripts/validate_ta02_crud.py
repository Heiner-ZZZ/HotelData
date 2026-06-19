from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))
PROJECT_ROOT = Path(__file__).resolve().parents[2]

from config.settings import get_settings
from src.app.features.ta02_crud.service import (
    CRUD_COLLECTIONS,
    SEARCH_FIELDS,
    create_document,
    delete_document,
    list_documents,
    update_document,
)
from src.database.connection import get_database


REPORT_PATH = PROJECT_ROOT / "data" / "reports" / "ta02_crud_validation_report.json"
EXPECTED_FACT_COUNT = 201000

KEY_FIELDS = {
    "fact_hotel_reservations": "source_record_id",
    "dim_hotels": "prop_id",
    "dim_destinations": "srch_destination_id",
    "dim_visitor_countries": "visitor_location_country_id",
    "dim_sites": "site_id",
    "dim_dates": "date_key",
    "dim_promotions": "promotion_flag",
    "dim_click_status": "click_bool",
    "dim_reservation_status": "reserva_bool",
    "dim_occupancy_profile": "occupancy_profile_id",
    "dim_stay_length_category": "stay_length_category_id",
    "dim_booking_window_category": "booking_window_category_id",
    "dim_price_category": "price_category_id",
}


def temp_key(collection_name: str, token: str) -> Any:
    if collection_name in {
        "dim_hotels",
        "dim_destinations",
        "dim_visitor_countries",
        "dim_sites",
        "dim_dates",
    }:
        return -int(token[-8:])
    if collection_name == "fact_hotel_reservations":
        return f"crud_validation_{token}"
    return f"CRUD_VALIDATION_{token}"


def temp_payload(collection_name: str, token: str) -> dict[str, Any]:
    key_field = KEY_FIELDS[collection_name]
    payload = {
        key_field: temp_key(collection_name, token),
        "validation_token": token,
        "created_by": "validate_ta02_crud.py",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if collection_name == "fact_hotel_reservations":
        payload.update(
            {
                "srch_id": -int(token[-8:]),
                "date_time": "2026-01-01T00:00:00+00:00",
                "date_key": 20260101,
                "site_id": -1,
                "visitor_location_country_id": -1,
                "prop_country_id": -1,
                "prop_id": -int(token[-8:]),
                "price_usd": 0.0,
                "promotion_flag": False,
                "srch_destination_id": -int(token[-8:]),
                "srch_length_of_stay": 1,
                "srch_booking_window": 1,
                "srch_adults_count": 1,
                "srch_children_count": 0,
                "srch_room_count": 1,
                "click_bool": False,
                "reserva_bool": False,
                "reservas_brutas_usd": 0.0,
                "execution_id": f"crud_validation_{token}",
            }
        )
    return payload


def search_value(collection_name: str, sample: dict[str, Any]) -> str:
    for field in SEARCH_FIELDS.get(collection_name, []):
        value = sample.get(field)
        if value is not None:
            if isinstance(value, bool):
                return "true" if value else "false"
            return str(value)
    return ""


def validate_collection(collection_name: str, token: str) -> dict[str, Any]:
    db = get_database()
    before_count = db[collection_name].count_documents({})
    result = {
        "collection": collection_name,
        "list_ok": False,
        "create_ok": False,
        "update_ok": False,
        "delete_ok": False,
        "search_ok": False,
        "errors": [],
    }
    created_id = None
    try:
        listed = list_documents(collection_name, page=1, page_size=25)
        result["list_ok"] = listed["page_size"] <= 25 and len(listed["items"]) <= 25

        if listed["items"]:
            q = search_value(collection_name, listed["items"][0])
            if q:
                searched = list_documents(collection_name, page=1, page_size=25, query=q)
                result["search_ok"] = searched["total"] >= 1 and len(searched["items"]) <= 25
            else:
                result["search_ok"] = True
        else:
            result["search_ok"] = True

        created = create_document(collection_name, temp_payload(collection_name, token))
        created_id = created["_id"]
        result["create_ok"] = created.get("validation_token") == token

        updated = update_document(collection_name, created_id, {"validation_updated": True})
        result["update_ok"] = bool(updated and updated.get("validation_updated") is True)

        deleted = delete_document(collection_name, created_id)
        created_id = None
        result["delete_ok"] = deleted.get("deleted_count") == 1

        after_count = db[collection_name].count_documents({})
        if after_count != before_count:
            result["errors"].append(f"Conteo cambio tras prueba temporal: antes={before_count}, despues={after_count}")
    except Exception as exc:
        result["errors"].append(str(exc))
        if created_id:
            try:
                delete_document(collection_name, created_id)
            except Exception as cleanup_exc:
                result["errors"].append(f"cleanup_failed: {cleanup_exc}")
    return result


def main() -> None:
    settings = get_settings()
    db = get_database()
    db.command("ping")

    token = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    fact_count_before = db.fact_hotel_reservations.count_documents({})
    collection_results = [validate_collection(name, token) for name in sorted(CRUD_COLLECTIONS)]
    fact_count_after = db.fact_hotel_reservations.count_documents({})

    global_errors = []
    if fact_count_before != EXPECTED_FACT_COUNT:
        global_errors.append(f"Conteo inicial fact_hotel_reservations esperado {EXPECTED_FACT_COUNT}, actual {fact_count_before}")
    if fact_count_after != EXPECTED_FACT_COUNT:
        global_errors.append(f"Conteo final fact_hotel_reservations esperado {EXPECTED_FACT_COUNT}, actual {fact_count_after}")

    report = {
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "mongo_database": settings.mongo_database,
        "fact_hotel_reservations_expected": EXPECTED_FACT_COUNT,
        "fact_hotel_reservations_before": fact_count_before,
        "fact_hotel_reservations_after": fact_count_after,
        "global_errors": global_errors,
        "collections": collection_results,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(report, indent=2, ensure_ascii=False))
    if global_errors or any(item["errors"] for item in collection_results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
