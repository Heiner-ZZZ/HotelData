from __future__ import annotations

import logging
from typing import Any

from src.app.modules.partner.services._common import normalize_label, split_multiline_tokens
from src.app.modules.partner.services.content.queries import content_page_for_prop
from src.database.connection import get_database

logger = logging.getLogger(__name__)

# ── In-memory cache for amenity price defaults (stored in hotel_content_pages with prop_id=0) ──
_PRICE_DEFAULTS_CACHE: dict[str, float] | None = None
_GLOBAL_DEFAULTS_PROP_ID = 0  # Sentinel prop_id for global amenity price defaults

DEFAULT_AMENITIES_CATALOG: dict[str, list[str]] = {
    "General": ["Wi-Fi", "Recepcion 24 horas", "Aire acondicionado", "Parking", "Piscina", "Gimnasio"],
    "Habitacion": ["TV", "Minibar", "Caja fuerte", "Balcon", "Servicio a la habitacion"],
    "Gastronomia": ["Desayuno incluido", "Restaurante", "Bar", "Cafe"],
    "Negocios": ["Centro de negocios", "Salas de reuniones"],
    "Familia": ["Habitaciones familiares", "Cunas", "Camas extra"],
    "Bienestar": ["Spa", "Sauna", "Masajes"],
    "Transporte": [
        "Traslado al aeropuerto",
        "Shuttle gratuito",
        "Valet parking",
        "Alquiler de auto",
        "Alquiler de bicicletas",
        "Transporte privado",
        "Taxi",
    ],
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


def _load_price_defaults_from_db() -> dict[str, float]:
    """Load global amenity price defaults from hotel_content_pages (prop_id=0).

    Returns empty dict if the document is missing or MongoDB is unavailable.
    Results are cached in module-level ``_PRICE_DEFAULTS_CACHE``.
    """
    global _PRICE_DEFAULTS_CACHE
    try:
        db = get_database()
        page = db.hotel_content_pages.find_one(
            {"prop_id": _GLOBAL_DEFAULTS_PROP_ID},
            {"_id": 0, "amenity_prices": 1},
        )
        defaults: dict[str, float] = {}
        raw_prices = (page or {}).get("amenity_prices") or {}
        for label, price in raw_prices.items():
            clean_label = (str(label) or "").strip().lower()
            if clean_label:
                try:
                    defaults[clean_label] = float(price)
                except (ValueError, TypeError):
                    defaults[clean_label] = 0.0

        _PRICE_DEFAULTS_CACHE = defaults
        if defaults:
            logger.info("Loaded %d global amenity price defaults from hotel_content_pages.", len(defaults))
        else:
            logger.warning(
                "No global amenity price defaults found (prop_id=0). "
                "All amenity prices will default to $0. "
                "Run seed_amenity_price_defaults.py to populate."
            )
        return defaults
    except Exception:
        logger.exception("Failed to load global amenity price defaults from MongoDB.")
        _PRICE_DEFAULTS_CACHE = {}
        return {}


def invalidate_price_defaults_cache() -> None:
    """Clear the in-memory cache so the next lookup re-reads from MongoDB."""
    global _PRICE_DEFAULTS_CACHE
    _PRICE_DEFAULTS_CACHE = None


def _get_price_defaults() -> dict[str, float]:
    """Return cached price defaults, loading from DB on first call."""
    global _PRICE_DEFAULTS_CACHE
    if _PRICE_DEFAULTS_CACHE is None:
        return _load_price_defaults_from_db()
    return _PRICE_DEFAULTS_CACHE


def _amenity_unit_price(label: str) -> float:
    """Return a default unit price for paid amenities, from MongoDB.

    Falls back to 0.0 if no default is configured for the given label.
    """
    return _get_price_defaults().get(label.lower(), 0.0)


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

    # Load stored overridden prices (label_lower -> price)
    stored_prices: dict[str, float] = {k.lower(): v for k, v in (page.get("amenity_prices") or {}).items()}

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
        # Use stored price if available, otherwise fall back to default
        unit_price = stored_prices.get(label.lower(), _amenity_unit_price(label))
        grouped.setdefault(category, []).append({
            "label": label,
            "active": label.lower() in active_lookup,
            "unit_price": unit_price,
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
