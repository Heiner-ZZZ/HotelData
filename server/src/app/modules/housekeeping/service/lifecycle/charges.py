"""Additional charges operations."""

from __future__ import annotations

from math import ceil
from typing import Any

from src.database.connection import get_database
from ..collections import CHARGES_COLLECTION
from ...schemas import AdditionalChargeCreate, now_iso


def create_additional_charge(payload: AdditionalChargeCreate) -> dict[str, Any] | None:
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": payload.booking_id})
    if not booking:
        return None
    now = now_iso()
    doc = {
        "booking_id": payload.booking_id, "prop_id": payload.prop_id,
        "concept": payload.concept, "amount": round(payload.amount, 2),
        "quantity": max(1, payload.quantity),
        "total": round(payload.amount * max(1, payload.quantity), 2),
        "category": payload.category or _infer_category(payload.concept),
        "note": payload.note, "created_at": now,
    }
    result = db[CHARGES_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _enrich_charge(doc)


def _infer_category(concept: str) -> str:
    """Infer charge category from concept text if not provided."""
    concept_lower = concept.lower()
    category_map = {
        "minibar": "minibar",
        "spa": "spa",
        "restaurante": "restaurante",
        "comida": "restaurante",
        "cena": "restaurante",
        "desayuno": "restaurante",
        "bar": "restaurante",
        "lavandería": "lavanderia",
        "lavanderia": "lavanderia",
        "parking": "parking",
        "estacionamiento": "parking",
        "mascota": "mascotas",
        "pet": "mascotas",
        "room service": "room_service",
        "habitación": "room_service",
        "daño": "danos",
        "daños": "danos",
        "damage": "danos",
        "late checkout": "late_checkout",
        "salida tarde": "late_checkout",
        "amenidad": "amenities",
    }
    for keyword, cat in category_map.items():
        if keyword in concept_lower:
            return cat
    return "otros"


def list_additional_charges(
    booking_id: str | None = None, prop_id: int | None = None,
    page: int = 1, page_size: int = 20,
) -> dict[str, Any]:
    db = get_database()
    query: dict[str, Any] = {}
    if booking_id:
        query["booking_id"] = booking_id
    if prop_id:
        query["prop_id"] = prop_id
    total = db[CHARGES_COLLECTION].count_documents(query)
    cursor = db[CHARGES_COLLECTION].find(query).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size)
    items = [_enrich_charge(doc) for doc in cursor]
    return {
        "items": items, "total": total, "page": page, "page_size": page_size,
        "total_pages": max(1, ceil(total / page_size)),
        "has_next": page * page_size < total, "has_prev": page > 1,
    }


def _enrich_charge(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    if "created_at" in doc:
        doc["created_at"] = _fmt(doc["created_at"])
    return doc


def _fmt(val):
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val) if val else None
