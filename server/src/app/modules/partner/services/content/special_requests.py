"""Per-hotel special-requests catalog.

Special requests ("Peticiones especiales") are the counterpart of amenities:
a per-hotel list of guest requests with a unit price and behavior flags.
Defaults live in code (like ``DEFAULT_AMENITIES_CATALOG``); each hotel can
override price/flags by label or add custom requests via
``hotel_content_pages.special_requests``.

Behavior flags:
- ``pet_related`` → validated against the hotel's ``pets_allowed`` policy at
  booking time; its price comes from the policy's ``pet_fee`` when set.
- ``high_floor`` → validated against the assigned room's ``floor`` and the
  hotel's ``high_floor_from`` threshold at booking time.
- ``late_arrival`` → informational; the guest wants a late check-in (used by
  the ETA / late check-in marker).

``chargeable`` is derived (unit_price > 0) and drives automatic charges.
"""
from __future__ import annotations

from typing import Any

from src.app.modules.partner.services._common import normalize_label
from src.app.modules.partner.services.content.queries import content_page_for_prop
from src.database.connection import get_database

DEFAULT_SPECIAL_REQUESTS: list[dict[str, Any]] = [
    {"label": "Cama extra", "unit_price": 15.0, "flags": ["chargeable"]},
    {"label": "Cuna para bebé", "unit_price": 10.0, "flags": ["chargeable"]},
    {"label": "Accesibilidad", "unit_price": 0.0, "flags": []},
    {"label": "Mascotas (Pet friendly)", "unit_price": 20.0, "flags": ["pet_related", "chargeable"]},
    {"label": "Piso alto", "unit_price": 0.0, "flags": ["high_floor"]},
    {"label": "Llegada tarde", "unit_price": 0.0, "flags": ["late_arrival"]},
]

# Behavior flags that survive from storage into the wire payload.
_BEHAVIOR_FLAGS = ("pet_related", "high_floor", "late_arrival")


def _expand(entry: dict[str, Any]) -> dict[str, Any]:
    flags = {str(f).strip().lower() for f in (entry.get("flags") or []) if str(f).strip()}
    unit_price = round(float(entry.get("unit_price") or 0.0), 2)
    payload: dict[str, Any] = {
        "label": str(entry.get("label") or ""),
        "unit_price": unit_price,
        "chargeable": unit_price > 0,
    }
    for flag in _BEHAVIOR_FLAGS:
        payload[flag] = flag in flags
    return payload


def _policy_pet_fee(prop_id: int) -> float:
    """Return the hotel's pet fee (``pet_fee``) from its hotel-wide policy, or 0."""
    try:
        db = get_database()
        policy = db.hotel_policies.find_one(
            {"prop_id": prop_id, "room_type_id": {"$in": ["", None]}, "rate_plan_id": {"$in": ["", None]}},
            {"_id": 0, "pet_fee": 1},
        )
        if policy:
            try:
                return round(float(policy.get("pet_fee") or 0.0), 2)
            except (ValueError, TypeError):
                return 0.0
    except Exception:
        pass
    return 0.0


def special_requests_payload_for_prop(prop_id: int) -> list[dict[str, Any]]:
    """Merge the default catalog with per-hotel overrides (by label).

    Stored entries replace the default's price and flags; custom labels are
    appended. For ``pet_related`` requests the hotel's policy ``pet_fee`` wins
    over the catalog price, so the charge the guest sees in the request is the
    one configured in Políticas.
    """
    page = content_page_for_prop(prop_id)
    stored = page.get("special_requests") or []

    # Defaults que el hotel eliminó explícitamente (tombstones escritos por
    # ``save_special_requests``) — no se re-mergean.
    removed = {normalize_label(r).lower() for r in (page.get("removed_requests") or [])}

    merged: dict[str, dict[str, Any]] = {}
    for entry in DEFAULT_SPECIAL_REQUESTS:
        key = normalize_label(entry["label"])
        if key.lower() in removed:
            continue
        merged[key] = dict(entry)
    for entry in stored:
        if not isinstance(entry, dict):
            continue
        label = str(entry.get("label") or "").strip()
        if not label:
            continue
        merged[normalize_label(label)] = {
            "label": label,
            "unit_price": entry.get("unit_price", 0.0),
            "flags": entry.get("flags") or [],
        }

    payload = [_expand(entry) for entry in merged.values()]

    pet_fee = _policy_pet_fee(prop_id)
    if pet_fee > 0:
        for item in payload:
            if item["pet_related"]:
                item["unit_price"] = pet_fee
                item["chargeable"] = True

    return payload


def special_requests_lookup(prop_id: int) -> dict[str, dict[str, Any]]:
    """Normalized-label → payload entry, for booking-time resolution."""
    return {normalize_label(item["label"]): item for item in special_requests_payload_for_prop(prop_id)}
