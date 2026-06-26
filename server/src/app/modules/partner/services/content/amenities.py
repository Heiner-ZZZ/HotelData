from __future__ import annotations

from typing import Any

from src.app.modules.partner.services._common import normalize_label, split_multiline_tokens
from src.app.modules.partner.services.content.queries import content_page_for_prop

DEFAULT_AMENITIES_CATALOG: dict[str, list[str]] = {
    "General": ["Wi-Fi", "Recepcion 24 horas", "Aire acondicionado", "Parking", "Piscina", "Gimnasio"],
    "Habitacion": ["TV", "Minibar", "Caja fuerte", "Balcon", "Servicio a la habitacion"],
    "Gastronomia": ["Desayuno incluido", "Restaurante", "Bar", "Cafe"],
    "Negocios": ["Centro de negocios", "Salas de reuniones"],
    "Familia": ["Habitaciones familiares", "Cunas", "Camas extra"],
    "Bienestar": ["Spa", "Sauna", "Masajes"],
}


def _amenity_category(label: str) -> str:
    normalized = label.lower()
    checks = [
        ("Habitacion", {"tv", "minibar", "caja fuerte", "balcon", "habitacion", "servicio a la habitacion"}),
        ("Gastronomia", {"desayuno", "restaurante", "bar", "cafe"}),
        ("Negocios", {"negocios", "reuniones", "business", "meeting"}),
        ("Familia", {"familia", "cuna", "camas extra", "ninos", "niños"}),
        ("Bienestar", {"spa", "sauna", "masajes", "wellness", "gimnasio"}),
        ("General", {"wifi", "wi-fi", "parking", "recepcion", "aire acondicionado", "pool", "piscina"}),
    ]
    for category, keywords in checks:
        if any(keyword in normalized for keyword in keywords):
            return category
    return "General"


def _amenity_unit_price(label: str) -> float:
    """Return a default unit price for paid amenities."""
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
        "sauna": 25.0,
        "servicio a la habitacion": 12.0,
        "servicio a la habitación": 12.0,
        "cafe": 5.0,
        "café": 5.0,
        "bar": 8.0,
        "restaurante": 0.0,
        "gimnasio": 10.0,
        "mascotas": 30.0,
        "pet friendly": 30.0,
    }
    return paid.get(label.lower(), 0.0)


def _build_catalog(active_items: list[str], page: dict[str, Any]) -> list[dict[str, Any]]:
    catalog_items: list[dict[str, str]] = []
    for category, labels in DEFAULT_AMENITIES_CATALOG.items():
        for label in labels:
            catalog_items.append({"category": category, "label": label})
    for item in page.get("amenities_catalog", []):
        label = normalize_label(item.get("label"))
        if label:
            catalog_items.append({"category": normalize_label(item.get("category")) or _amenity_category(label), "label": label})
    for label in active_items:
        catalog_items.append({"category": _amenity_category(label), "label": label})

    seen: set[tuple[str, str]] = set()
    grouped: dict[str, list[dict[str, Any]]] = {}
    active_lookup = {item.lower() for item in active_items}
    for item in catalog_items:
        category = normalize_label(item.get("category")) or "General"
        label = normalize_label(item.get("label"))
        key = (category.lower(), label.lower())
        if not label or key in seen:
            continue
        seen.add(key)
        grouped.setdefault(category, []).append({
            "label": label,
            "active": label.lower() in active_lookup,
            "unit_price": _amenity_unit_price(label),
        })

    return [
        {"category": category, "items": sorted(items, key=lambda entry: entry["label"].lower())}
        for category, items in grouped.items()
    ]


def amenities_payload_for_prop(prop_id: int, room_type_id: str = "") -> dict[str, Any]:
    page = content_page_for_prop(prop_id)
    active_items: list[str] = []

    if room_type_id:
        room_amenities = page.get("room_amenities", {})
        room_data = room_amenities.get(room_type_id, {})
        active_items = [normalize_label(item) for item in room_data.get("active_amenities", []) if normalize_label(item)]
        if not active_items:
            active_items = split_multiline_tokens(room_data.get("amenities_text", ""))
    else:
        stored_active = [normalize_label(item) for item in page.get("active_amenities", []) if normalize_label(item)]
        parsed_active = split_multiline_tokens(page.get("amenities_text"))
        active_items = stored_active or parsed_active

    return {
        "active_amenities": active_items,
        "catalog": _build_catalog(active_items, page),
    }
