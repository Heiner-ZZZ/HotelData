"""Room features: configurable attribute tags for room types.

Each room type can have multiple feature tags like "Ocean View",
"Balcony", "Non-Smoking", "Accessible", "Quiet Zone", etc.

Features are stored as a simple array of strings on the room_type document
under the ``features`` field. A master catalog of available feature labels
is maintained in ``room_features`` collection for UI autocomplete.
"""

from __future__ import annotations

from typing import Any

from pymongo import ReturnDocument

from src.app.modules.partner.services._common import clean_text, now_utc
from src.app.modules.partner.services.audit import register_action
from src.app.modules.partner.services.content.amenities import DEFAULT_AMENITIES_CATALOG, _amenity_unit_price as _amenity_default_price
from src.database.connection import get_database

# Predefined default feature catalog for hotel room types
DEFAULT_FEATURES: list[str] = [
    "Vista al mar",
    "Vista a la ciudad",
    "Vista al jardín",
    "Vista a la piscina",
    "Balcón",
    "Terraza",
    "No fumadores",
    "Accesible",
    "Zona tranquila",
    "Suite ejecutiva",
    "Habitación familiar",
    "Habitación contigua",
    "Planta baja",
    "Último piso",
    "Cerca del ascensor",
    "Cama king",
    "Camas twin",
    "Sofá cama",
    "Cama extra",
    "Baño privado",
    "Baño compartido",
    "Ducha de lluvia",
    "Bañera de hidromasaje",
    "Chimenea",
    "Cocina equipada",
    "Microondas",
    "Lavadora",
    "Secadora",
    "Escritorio",
    "Sillón",
    "Vestidor",
    "Aire acondicionado",
    "Calefacción",
    "Suelo radiante",
    "Ventanas insonorizadas",
    "Cortinas blackout",
    "Caja fuerte",
    "Minibar",
    "TV",
    "Netflix",
    "Wi-Fi de alta velocidad",
    "Carga USB",
    "Altavoz bluetooth",
    "Despertador",
    "Plancha",
    "Secador de pelo",
    "Espejo de aumento",
    "Artículos de aseo",
    "Albornoz",
    "Zapatillas",
    "Cuna disponible",
    "Trona disponible",
    "Juegos de mesa",
    "Servicio a la habitación",
    "Desayuno en habitación",
]

# Predefined categories for features
FEATURE_CATEGORIES: dict[str, list[str]] = {
    "Vistas": ["Vista al mar", "Vista a la ciudad", "Vista al jardín", "Vista a la piscina"],
    "Espacio exterior": ["Balcón", "Terraza"],
    "Tipo": ["No fumadores", "Accesible", "Zona tranquila", "Suite ejecutiva", "Habitación familiar", "Habitación contigua"],
    "Ubicación": ["Planta baja", "Último piso", "Cerca del ascensor"],
    "Camas": ["Cama king", "Camas twin", "Sofá cama", "Cama extra"],
    "Baño": ["Baño privado", "Baño compartido", "Ducha de lluvia", "Bañera de hidromasaje"],
    "Equipamiento": ["Chimenea", "Cocina equipada", "Microondas", "Lavadora", "Secadora", "Escritorio", "Sillón", "Vestidor"],
    "Climatización": ["Aire acondicionado", "Calefacción", "Suelo radiante", "Ventanas insonorizadas", "Cortinas blackout"],
    "Tecnología": ["Caja fuerte", "Minibar", "TV", "Netflix", "Wi-Fi de alta velocidad", "Carga USB", "Altavoz bluetooth", "Despertador"],
    "Comodidades": ["Plancha", "Secador de pelo", "Espejo de aumento", "Artículos de aseo", "Albornoz", "Zapatillas"],
    "Familiar": ["Cuna disponible", "Trona disponible", "Juegos de mesa"],
    "Servicios": ["Servicio a la habitación", "Desayuno en habitación"],
}


def _get_feature_category(label: str) -> str:
    """Return the category for a feature label."""
    normalized = label.lower()
    for category, items in FEATURE_CATEGORIES.items():
        for item in items:
            if item.lower() == normalized:
                return category
    return "Otros"


def _feature_unit_price(label: str) -> float:
    """Return a default unit_price for a feature label.
    Features with special pricing, others are included in room price."""
    paid_features = {
        "cama extra": 25.0,
        "cuna disponible": 15.0,
        "trona disponible": 10.0,
        "desayuno en habitación": 18.0,
        "servicio a la habitación": 12.0,
        "caja fuerte": 5.0,
        "minibar": 15.0,
        "netflix": 8.0,
        "altavoz bluetooth": 5.0,
        "estacionamiento": 20.0,
        "parking": 20.0,
        "mascotas": 30.0,
        "pet fee": 30.0,
    }
    return paid_features.get(label.lower(), 0.0)


def get_all_features() -> list[dict[str, Any]]:
    """Return the master catalog of available features, grouped by category.

    Sources (priority order):
      1. ``room_features`` collection (custom user-created features)
      2. Hardcoded ``FEATURE_CATEGORIES`` (room-specific attributes)
      3. ``DEFAULT_AMENITIES_CATALOG`` (property-level amenities, de-duped)
    """
    db = get_database()
    custom = list(
        db.room_features.find({}, {"_id": 0, "label": 1, "category": 1, "icon": 1, "unit_price": 1})
        .sort([("category", 1), ("label", 1)])
    )
    seen_labels: set[str] = set()
    for feat in custom:
        seen_labels.add(feat.get("label", "").lower())

    merged: dict[str, list[dict[str, Any]]] = {}
    for category, labels in FEATURE_CATEGORIES.items():
        merged[category] = [
            {
                "label": label,
                "category": category,
                "icon": _feature_icon(label),
                "custom": False,
                "source": "feature",
                "unit_price": _feature_unit_price(label),
            }
            for label in labels
            if label.lower() not in seen_labels
        ]
    for feat in custom:
        cat = feat.get("category") or _get_feature_category(feat.get("label", ""))
        merged.setdefault(cat, []).append({
            "label": feat["label"],
            "category": cat,
            "icon": feat.get("icon", ""),
            "custom": True,
            "source": "custom",
            "unit_price": float(feat.get("unit_price", 0) or 0),
        })

    # Merge amenity catalog items (de-duped against existing labels)
    for category, labels in DEFAULT_AMENITIES_CATALOG.items():
        for label in labels:
            if label.lower() in seen_labels:
                continue
            seen_labels.add(label.lower())
            merged.setdefault(category, []).append({
                "label": label,
                "category": category,
                "icon": _feature_icon(label),
                "custom": False,
                "source": "amenity",
                "unit_price": _amenity_default_price(label),
            })

    result = []
    for category in sorted(merged.keys()):
        items = merged[category]
        items.sort(key=lambda x: x["label"].lower())
        result.append({"category": category, "items": items})
    return result


def _feature_icon(label: str) -> str:
    """Map a feature label to a Material Symbols icon name."""
    icon_map: dict[str, str] = {
        "vista al mar": "beach_access",
        "vista a la ciudad": "city",
        "vista al jardín": "yard",
        "vista a la piscina": "pool",
        "balcón": "balcony",
        "terraza": "deck",
        "no fumadores": "smoke_free",
        "accesible": "accessible",
        "zona tranquila": "quiet_zone",
        "suite ejecutiva": "workspace_premium",
        "habitación familiar": "family_restroom",
        "habitación contigua": "door_sliding",
        "planta baja": "ground_floor",
        "último piso": "penthouse",
        "cerca del ascensor": "elevator",
        "cama king": "king_bed",
        "camas twin": "bed",
        "sofá cama": "airline_seat_recline_normal",
        "cama extra": "bedroom_parent",
        "baño privado": "bathtub",
        "baño compartido": "shower",
        "ducha de lluvia": "rain_shower",
        "bañera de hidromasaje": "hot_tub",
        "chimenea": "fireplace",
        "cocina equipada": "cooking",
        "microondas": "microwave",
        "lavadora": "local_laundry_service",
        "secadora": "dry",
        "escritorio": "desk",
        "sillón": "chair",
        "vestidor": "dresser",
        "aire acondicionado": "ac_unit",
        "calefacción": "heat_pump",
        "suelo radiante": "radiator",
        "ventanas insonorizadas": "sounds",
        "cortinas blackout": "blinds",
        "caja fuerte": "safe",
        "minibar": "local_bar",
        "tv": "tv",
        "netflix": "subscriptions",
        "wi-fi de alta velocidad": "wifi",
        "carga usb": "usb",
        "altavoz bluetooth": "speaker",
        "despertador": "alarm",
        "plancha": "iron",
        "secador de pelo": "air_freshener",
        "espejo de aumento": "mirror",
        "artículos de aseo": "soap",
        "albornoz": "bathroom",
        "zapatillas": "slippers",
        "cuna disponible": "crib",
        "trona disponible": "table_restaurant",
        "juegos de mesa": "board_game",
        "servicio a la habitación": "room_service",
        "desayuno en habitación": "breakfast_dining",
        "wi-fi": "wifi",
        "recepcion 24 horas": "support_agent",
        "recepcion": "support_agent",
        "parking": "local_parking",
        "piscina": "pool",
        "gimnasio": "fitness_center",
        "restaurante": "restaurant",
        "bar": "local_bar",
        "cafe": "coffee",
        "café": "coffee",
        "centro de negocios": "business_center",
        "salas de reuniones": "meeting_room",
        "habitaciones familiares": "family_restroom",
        "cunas": "crib",
        "spa": "spa",
        "sauna": "sauna",
        "masajes": "massage",
    }
    return icon_map.get(label.lower(), "check")


def _normalize_features(raw: Any) -> list[dict[str, Any]]:
    """Normalize features from DB (strings or objects) to a list of dicts."""
    if not isinstance(raw, list):
        return []
    result: list[dict[str, Any]] = []
    for f in raw:
        if isinstance(f, dict):
            result.append({
                "label": str(f.get("label", "")),
                "unit_price": float(f.get("unit_price", 0) or 0),
            })
        elif isinstance(f, str):
            result.append({
                "label": f,
                "unit_price": _feature_unit_price(f),
            })
    return result


def get_room_type_features(prop_id: int, room_type_id: str) -> list[dict[str, Any]]:
    """Return the feature tags (with prices) for a specific room type."""
    db = get_database()
    room = db.room_types.find_one(
        {"prop_id": prop_id, "room_type_id": room_type_id},
        {"_id": 0, "features": 1},
    )
    if room is None:
        return []
    return _normalize_features(room.get("features", []))


def update_room_type_features(
    prop_id: int,
    room_type_id: str,
    *,
    features: list[str] | list[dict[str, Any]],
    changed_by: str = "angular_api",
) -> dict[str, Any] | None:
    """Set the feature tags (with optional unit_price) for a room type.

    Accepts either:
      - list of strings: legacy format, prices from catalog defaults
      - list of dicts with ``label`` and optional ``unit_price``
    """
    db = get_database()
    from pydantic import BaseModel, Field
    room = db.room_types.find_one(
        {"prop_id": prop_id, "room_type_id": room_type_id},
        {"_id": 0, "name": 1},
    )
    if room is None:
        return None

    clean_objects: list[dict[str, Any]] = []
    seen: set[str] = set()
    for feat in features:
        if isinstance(feat, dict):
            label = clean_text(str(feat.get("label", "")))
            unit_price = float(feat.get("unit_price", 0) or 0)
        else:
            label = clean_text(str(feat))
            unit_price = _feature_unit_price(label)
        key = label.lower()
        if label and key not in seen:
            seen.add(key)
            clean_objects.append({"label": label, "unit_price": unit_price})

    result = db.room_types.find_one_and_update(
        {"prop_id": prop_id, "room_type_id": room_type_id},
        {"$set": {"features": clean_objects, "updated_at": now_utc()}},
        return_document=ReturnDocument.AFTER,
        projection={"_id": 0},
    )

    room_name = room.get("name", room_type_id)
    register_action(
        prop_id=prop_id,
        entity_type="room_type",
        entity_id=room_type_id,
        action="update",
        summary=f"Características de '{room_name}' actualizadas: {len(clean_objects)} atributos",
        changed_by=changed_by,
        metadata={"features_count": len(clean_objects)},
    )
    return result


def add_custom_feature(
    *,
    label: str,
    category: str = "",
    icon: str = "",
    changed_by: str = "angular_api",
) -> dict[str, Any] | None:
    """Add a custom feature to the master catalog."""
    db = get_database()
    clean_label = clean_text(label)
    if not clean_label:
        raise ValueError("Debe indicar un nombre para la característica.")

    clean_category = clean_text(category) or _get_feature_category(clean_label)
    clean_icon = clean_text(icon) or _feature_icon(clean_label)

    existing = db.room_features.find_one({"label": clean_label}, {"_id": 1})
    if existing is not None:
        raise ValueError(f"La característica '{clean_label}' ya existe.")

    doc = {
        "label": clean_label,
        "category": clean_category,
        "icon": clean_icon,
        "created_by": changed_by,
        "created_at": now_utc(),
    }
    db.room_features.insert_one(doc)
    return doc
