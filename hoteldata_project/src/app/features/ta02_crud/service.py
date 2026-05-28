from __future__ import annotations

from math import ceil
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

from src.database.connection import get_database


FACT_HOTEL_RESERVATION_COLUMNS = [
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

CRUD_COLLECTIONS = {
    "fact_hotel_reservations",
    "dim_hotels",
    "dim_destinations",
    "dim_visitor_countries",
    "dim_sites",
    "dim_dates",
    "dim_promotions",
    "dim_click_status",
    "dim_reservation_status",
    "dim_stay_length_category",
    "dim_booking_window_category",
    "dim_price_category",
    "dim_occupancy_profile",
}

SEARCH_FIELDS = {
    "fact_hotel_reservations": [
        "source_record_id",
        "srch_id",
        "prop_id",
        "srch_destination_id",
        "visitor_location_country_id",
        "execution_id",
    ],
    "dim_hotels": ["prop_id"],
    "dim_destinations": ["srch_destination_id"],
    "dim_visitor_countries": ["visitor_location_country_id"],
    "dim_sites": ["site_id"],
    "dim_dates": ["date_key"],
    "dim_promotions": ["promotion_flag"],
    "dim_click_status": ["click_bool"],
    "dim_reservation_status": ["reserva_bool"],
    "dim_occupancy_profile": ["occupancy_profile_id"],
    "dim_stay_length_category": ["stay_length_category_id"],
    "dim_booking_window_category": ["booking_window_category_id"],
    "dim_price_category": ["price_category_id"],
}

COLLECTION_LABELS = {
    "fact_hotel_reservations": "Tabla de hecho: reservas hoteleras",
    "dim_hotels": "Hoteles",
    "dim_destinations": "Destinos",
    "dim_visitor_countries": "Paises visitantes",
    "dim_sites": "Sitios",
    "dim_dates": "Fechas",
    "dim_promotions": "Promociones",
    "dim_click_status": "Estado de click",
    "dim_reservation_status": "Estado de reserva",
    "dim_occupancy_profile": "Perfil de ocupacion",
    "dim_stay_length_category": "Categoria de estancia",
    "dim_booking_window_category": "Categoria de anticipacion",
    "dim_price_category": "Categoria de precio",
}

COLLECTION_SHORT_LABELS = {
    "fact_hotel_reservations": "Reservas hoteleras",
    "dim_hotels": "Hoteles",
    "dim_destinations": "Destinos",
    "dim_visitor_countries": "Paises visitantes",
    "dim_sites": "Sitios",
    "dim_dates": "Fechas",
    "dim_promotions": "Promociones",
    "dim_click_status": "Estado de click",
    "dim_reservation_status": "Estado de reserva",
    "dim_stay_length_category": "Categoria de estancia",
    "dim_booking_window_category": "Categoria de anticipacion",
    "dim_price_category": "Categoria de precio",
    "dim_occupancy_profile": "Perfil de ocupacion",
}

DISPLAY_COLUMNS = {
    "fact_hotel_reservations": FACT_HOTEL_RESERVATION_COLUMNS,
}


def default_payload(collection_name: str) -> dict[str, Any]:
    return {}


def _serialize(document: dict[str, Any]) -> dict[str, Any]:
    if "_id" in document:
        document["_id"] = str(document["_id"])
    return document


def _parse_query_value(value: str, include_bool: bool = False) -> list[Any]:
    text = value.strip()
    values: list[Any] = [text]
    lowered = text.lower()
    if include_bool and lowered in {"true", "false"}:
        values.append(lowered == "true")
    if include_bool and lowered in {"1", "0"}:
        values.append(lowered == "1")
    try:
        values.append(int(text))
    except ValueError:
        pass
    try:
        values.append(float(text))
    except ValueError:
        pass
    deduped = []
    for item in values:
        if not any(type(item) is type(existing) and item == existing for existing in deduped):
            deduped.append(item)
    return deduped


def _build_search_filter(collection_name: str, query: str = "") -> dict[str, Any]:
    query = query.strip()
    if not query:
        return {}
    clauses = []
    for field in SEARCH_FIELDS.get(collection_name, []):
        if field.endswith("_bool") or field in {"promotion_flag"}:
            for value in _parse_query_value(query, include_bool=True):
                if isinstance(value, bool):
                    clauses.append({field: value})
        elif field in {"execution_id", "source_record_id"}:
            clauses.append({field: {"$regex": query, "$options": "i"}})
        elif field.endswith("_id") or field.endswith("_key") or field in {"srch_id", "site_id"}:
            for value in _parse_query_value(query):
                clauses.append({field: value})
        else:
            clauses.append({field: {"$regex": query, "$options": "i"}})
    return {"$or": clauses} if clauses else {}


def _collection(name: str):
    if name not in CRUD_COLLECTIONS:
        raise ValueError(f"Collection is not exposed for TA 02 CRUD: {name}")
    return get_database()[name]


def list_documents(collection_name: str, page: int = 1, page_size: int = 25, query: str = "") -> dict[str, Any]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 25)
    collection = _collection(collection_name)
    filters = _build_search_filter(collection_name, query)
    total = collection.count_documents(filters)
    total_pages = ceil(total / page_size) if total else 0
    if total_pages and page > total_pages:
        page = total_pages
    cursor = collection.find(filters)
    if collection_name == "fact_hotel_reservations":
        cursor = cursor.sort([("date_time", -1), ("srch_id", 1), ("prop_id", 1)])
    items = [_serialize(item) for item in cursor.skip((page - 1) * page_size).limit(page_size)]
    return {
        "collection": collection_name,
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "query": query,
        "search_fields": SEARCH_FIELDS.get(collection_name, []),
        "total_pages": total_pages,
        "has_next": total_pages > 0 and page < total_pages,
        "has_prev": page > 1 and total_pages > 0,
}


def display_columns(collection_name: str, items: list[dict[str, Any]] | None = None) -> list[str]:
    configured = DISPLAY_COLUMNS.get(collection_name)
    if configured:
        return configured
    columns: list[str] = []
    for item in items or []:
        for key in item.keys():
            if key not in columns:
                columns.append(key)
    return columns


def get_document(collection_name: str, document_id: str) -> dict[str, Any] | None:
    try:
        object_id = ObjectId(document_id)
    except InvalidId:
        return None
    document = _collection(collection_name).find_one({"_id": object_id})
    return _serialize(document) if document else None


def create_document(collection_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    payload.pop("_id", None)
    result = _collection(collection_name).insert_one(payload)
    return get_document(collection_name, str(result.inserted_id)) or {"_id": str(result.inserted_id)}


def update_document(collection_name: str, document_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    payload.pop("_id", None)
    try:
        object_id = ObjectId(document_id)
    except InvalidId:
        return None
    _collection(collection_name).update_one({"_id": object_id}, {"$set": payload})
    return get_document(collection_name, document_id)


def delete_document(collection_name: str, document_id: str) -> dict[str, Any]:
    try:
        object_id = ObjectId(document_id)
    except InvalidId:
        return {"deleted_count": 0}
    result = _collection(collection_name).delete_one({"_id": object_id})
    return {"deleted_count": result.deleted_count}


def collection_metadata() -> list[dict[str, Any]]:
    ordered = ["fact_hotel_reservations"] + sorted(name for name in CRUD_COLLECTIONS if name != "fact_hotel_reservations")
    return [
        {
            "name": name,
            "label": COLLECTION_LABELS.get(name, name),
            "short_label": COLLECTION_SHORT_LABELS.get(name, name),
            "search_fields": SEARCH_FIELDS.get(name, []),
        }
        for name in ordered
    ]
