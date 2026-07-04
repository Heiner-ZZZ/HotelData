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
    category = payload.category or _infer_category(payload.concept)
    total = round(payload.amount * max(1, payload.quantity), 2)
    doc = {
        "booking_id": payload.booking_id, "prop_id": payload.prop_id,
        "concept": payload.concept, "amount": round(payload.amount, 2),
        "quantity": max(1, payload.quantity),
        "total": total,
        "category": category,
        "note": payload.note, "created_at": now,
    }
    result = db[CHARGES_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id

    # ── Auto-post to the guest folio ──
    try:
        from src.app.modules.billing.service.folio import post_to_folio
        post_to_folio(
            payload.booking_id,
            posting_type="charge",
            category=category,
            concept=payload.concept,
            amount=total,
            quantity=payload.quantity,
            reference_id=str(result.inserted_id),
            reference_type="additional_charge",
        )
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            "Failed to auto-post charge to folio for booking %s", payload.booking_id
        )

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


def delete_additional_charge(charge_id: str) -> dict | None:
    """Delete an additional charge by its ID."""
    db = get_database()
    try:
        from bson import ObjectId
        obj_id = ObjectId(charge_id)
    except Exception:
        return None

    charge = db[CHARGES_COLLECTION].find_one({"_id": obj_id})
    if not charge:
        return None

    db[CHARGES_COLLECTION].delete_one({"_id": obj_id})

    # Reverse the folio posting
    try:
        from src.app.modules.billing.service.folio import post_to_folio
        post_to_folio(
            charge.get("booking_id", ""),
            posting_type="adjustment",
            category=charge.get("category", "otros"),
            concept=f"[ANULADO] {charge.get('concept', '')}",
            amount=-abs(float(charge.get("total", 0))),
            quantity=charge.get("quantity", 1),
            reference_id=charge_id,
            reference_type="charge_reversal",
        )
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            "Failed to reverse folio posting for deleted charge %s", charge_id
        )

    return {"ok": True, "deleted_id": charge_id, "booking_id": charge.get("booking_id", "")}


def _enrich_charge(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    if "created_at" in doc:
        doc["created_at"] = _fmt(doc["created_at"])
    return doc


def _fmt(val):
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val) if val else None
