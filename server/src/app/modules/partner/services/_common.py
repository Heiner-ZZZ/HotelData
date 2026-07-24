"""Shared utilities for the partner sub-services.

This module is the *only* place that owns cross-cutting helpers
(datetime, formatting, parsing, fact-collection resolution, change-log
registration) shared by `properties`, `content`, `rooms`, `rates` and
`dashboard`. It must not import any other `services` sub-module.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pymongo.collection import Collection

from src.database.connection import get_database


def now_utc() -> datetime:
    return datetime.now(UTC)


def safe_int(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or not text.lstrip("-").isdigit():
        return None
    return int(text)


def safe_positive_int(value: Any, default: int = 0) -> int:
    parsed = safe_int(value)
    if parsed is None:
        return default
    return max(parsed, 0)


def safe_bool(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return text in {"1", "true", "on", "yes", "si"}


def money(value: Any) -> str:
    if value is None:
        return "N/D"
    return f"{float(value):,.2f}"


def number(value: Any, decimals: int = 1) -> str:
    if value is None:
        return "N/D"
    return f"{float(value):,.{decimals}f}"


def iso_label(value: Any) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value or "")


def clean_text(value: Any) -> str:
    return str(value or "").strip()


def normalize_label(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def split_multiline_tokens(value: Any) -> list[str]:
    text = str(value or "")
    normalized = text.replace("\r", "\n").replace(";", "\n").replace(",", "\n")
    items: list[str] = []
    for chunk in normalized.split("\n"):
        clean = normalize_label(chunk.lstrip("-* ").strip())
        if clean:
            items.append(clean)
    return items


def slugify(value: str) -> str:
    text = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in text:
        text = text.replace("--", "-")
    return text.strip("-") or "room"


def hotel_display_name(hotel: dict[str, Any] | None, prop_id: int) -> str:
    if not hotel:
        return f"Hotel Partner {prop_id}"
    return (
        hotel.get("display_name")
        or hotel.get("hotel_name")
        or f"Hotel Partner {prop_id}"
    )


def destination_display_name(destination: dict[str, Any] | None, destination_id: int) -> str:
    if not destination:
        return f"Destino {destination_id}"
    return (
        destination.get("destination_name")
        or f"Destino {destination_id}"
    )


def _resolve_country_name(country_id: int | None) -> str:
    """Resolve a prop_country_id to its display name from dim_visitor_countries.

    The geo-catalog admin page (/admin/geo-catalog) lets admins set
    country_display_name per visitor_location_country_id. This function
    queries that collection first, falling back to a generic label.
    """
    if country_id is None:
        return "N/D"
    db = get_database()
    country = db.dim_visitor_countries.find_one(
        {"visitor_location_country_id": country_id},
        {"_id": 0, "country_name": 1},
    )
    if country:
        return (
            country.get("country_name")
            or f"Mercado hotelero {country_id}"
        )
    return f"Mercado hotelero {country_id}"


def _resolve_country_label(hotel: dict[str, Any] | None) -> str:
    """Resolve the best country display name for a hotel dict.

    Priority:
      1. display_country_label IF it's a proper name (not the "Mercado hotelero" fallback)
      2. _resolve_country_name from dim_visitor_countries
      3. "N/D" as last resort
    """
    if not hotel:
        return "N/D"
    manual_label = hotel.get("display_country_label") or ""
    # If the stored label is the old fallback, ignore it and resolve fresh
    if manual_label.startswith("Mercado hotelero"):
        manual_label = ""
    if manual_label:
        return manual_label
    return _resolve_country_name(hotel.get("prop_country_id"))


def active_fact_collection() -> tuple[Collection, str]:
    db = get_database()
    if db.fact_hotel_reservations.estimated_document_count() > 0:
        return db.fact_hotel_reservations, "fact_hotel_reservations"
    return db.fact_hotel_events, "fact_hotel_events"


def register_content_change(
    prop_id: int,
    entity_type: str,
    action: str,
    payload: dict[str, Any],
    changed_by: str = "partner_web",
) -> None:
    db = get_database()
    db.hotel_content_changes.insert_one(
        {
            "prop_id": prop_id,
            "entity_type": entity_type,
            "action": action,
            "payload": payload,
            "changed_by": changed_by,
            "changed_at": now_utc(),
        }
    )
