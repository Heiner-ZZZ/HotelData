"""Service to fetch billable amenity services for the billing invoice page.

Combines hotel-wide amenities with room-type-specific amenities,
deduplicates by label, and returns them categorized for quick-charge
and category-dropdown use on the invoice detail page.
"""

from __future__ import annotations

from typing import Any

from src.database.connection import get_database
from src.app.modules.partner.services._common import normalize_label


def get_billable_services(prop_id: int, booking_id: str | None = None) -> dict[str, Any]:
    """Return categorized services available for charging on an invoice.

    Merges hotel-wide amenities with room-type-specific amenities for the
    given booking, deduplicated by label (case-insensitive). Includes both
    free (unit_price=0) and paid (unit_price>0) services so the frontend
    can decide which to show as quick-charge vs. included.

    Returns
    -------
    dict with keys:
        categories : list[dict]
            Each entry: {category, items: [{label, unit_price}]}
            Grouped by amenity category, items sorted alphabetically.
        chargeable  : list[dict]
            Flat list of items where unit_price > 0 (suitable for quick-charge).
        all_items  : list[dict]
            Flat deduplicated list of ALL items, each with {label, unit_price, category}.
    """
    db = get_database()
    page = db.hotel_content_pages.find_one({"prop_id": prop_id}, {"_id": 0})
    if not page:
        return {"categories": [], "chargeable": [], "all_items": []}

    # 1. Collect active items with their categories and prices
    stored_prices: dict[str, float] = {k.lower(): v for k, v in (page.get("amenity_prices") or {}).items()}
    seen: dict[str, dict[str, Any]] = {}  # label_lower -> item

    # Helper: add items from any source
    def _merge(labels: list[str], category: str | None = None) -> None:
        for label in labels:
            clean = normalize_label(label)
            if not clean or clean.lower() in seen:
                continue
            cat = category or _category_for_label(clean)
            unit_price = stored_prices.get(clean.lower(), _default_price(clean))
            seen[clean.lower()] = {
                "label": clean,
                "category": cat,
                "unit_price": unit_price,
            }

    # 2. Hotel-wide active amenities
    hotel_active: list[str] = []
    for item in page.get("active_amenities", []) or []:
        cleaned = normalize_label(item)
        if cleaned:
            hotel_active.append(cleaned)
    # Also parse from amenities_text if active_amenities is empty
    if not hotel_active and page.get("amenities_text"):
        hotel_active = [normalize_label(t) for t in page["amenities_text"].split(",") if normalize_label(t)]

    _merge(hotel_active)

    # 3. Room-type-specific amenities (if booking_id provided)
    room_type_id: str | None = None
    if booking_id:
        booking = db.booking_orders.find_one(
            {"booking_id": booking_id},
            {"room_type_id": 1, "_id": 0},
        )
        if booking:
            room_type_id = booking.get("room_type_id")

    if room_type_id:
        room_amenities = page.get("room_amenities", {}) or {}
        room_data = room_amenities.get(room_type_id, {})
        room_active: list[str] = []
        for item in room_data.get("active_amenities", []) or []:
            cleaned = normalize_label(item)
            if cleaned:
                room_active.append(cleaned)
        if not room_active and room_data.get("amenities_text"):
            room_active = [normalize_label(t) for t in room_data["amenities_text"].split(",") if normalize_label(t)]
        _merge(room_active)

    # 4. Group by category
    grouped: dict[str, list[dict[str, Any]]] = {}
    all_items: list[dict[str, Any]] = []
    chargeable: list[dict[str, Any]] = []

    for item in seen.values():
        cat = item["category"]
        entry = {"label": item["label"], "unit_price": item["unit_price"]}
        grouped.setdefault(cat, []).append(entry)
        all_items.append(entry)
        if item["unit_price"] > 0:
            chargeable.append(entry)

    categories = [
        {"category": cat, "items": sorted(items, key=lambda x: x["label"].lower())}
        for cat, items in sorted(grouped.items())
    ]

    chargeable.sort(key=lambda x: x["label"].lower())
    all_items.sort(key=lambda x: x["label"].lower())

    return {
        "categories": categories,
        "chargeable": chargeable,
        "all_items": all_items,
    }


def _category_for_label(label: str) -> str:
    """Return the amenity category based on label keywords."""
    normalized = label.lower()
    checks = [
        ("Habitacion", {"tv", "minibar", "caja fuerte", "balcon", "habitacion", "servicio a la habitacion", "cuna", "camas extra", "plancha", "secador", "nevera", "microondas", "television"}),
        ("Gastronomia", {"desayuno", "restaurante", "bar", "cafe", "cafetería", "buffet", "snack", "minibar", "cocina"}),
        ("Bienestar", {"spa", "sauna", "masajes", "wellness", "gimnasio", "yoga"}),
        ("Negocios", {"negocios", "reuniones", "business", "meeting", "salon"}),
        ("Familia", {"familia", "cuna", "camas extra", "ninos", "niños"}),
        ("Lavanderia", {"lavandería", "lavanderia", "laundry", "lavado", "tintorería", "limpieza"}),
        ("Mascotas", {"mascota", "mascotas", "perro", "pet"}),
        ("Parking", {"parking", "estacionamiento", "parqueo", "garaje"}),
        ("General", {"wifi", "wi-fi", "internet", "recepcion", "aire acondicionado", "pool", "piscina", "gimnasio"}),
    ]
    for cat, keywords in checks:
        if any(kw in normalized for kw in keywords):
            return cat
    return "General"


def _default_price(label: str) -> float:
    """Return a sensible default unit price for common paid amenities."""
    paid = {
        "desayuno incluido": 15.0,
        "desayuno": 15.0,
        "camas extra": 25.0,
        "cama extra": 25.0,
        "cunas": 15.0,
        "cuna": 15.0,
        "parking": 20.0,
        "estacionamiento": 20.0,
        "minibar": 15.0,
        "caja fuerte": 5.0,
        "spa": 40.0,
        "masajes": 50.0,
        "masaje": 50.0,
        "sauna": 25.0,
        "servicio a la habitacion": 12.0,
        "servicio a la habitación": 12.0,
        "cafe": 5.0,
        "café": 5.0,
        "bar": 8.0,
        "restaurante": 0.0,
        "gimnasio": 10.0,
        "mascotas": 30.0,
        "mascota": 30.0,
        "pet friendly": 30.0,
        "lavandería": 18.0,
        "lavanderia": 18.0,
        "laundry": 18.0,
        "late check-out": 35.0,
        "late checkout": 35.0,
    }
    return paid.get(label.lower(), 0.0)
