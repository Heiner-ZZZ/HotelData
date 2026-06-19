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
        or hotel.get("hotel_label")
        or f"Hotel Partner {prop_id}"
    )


def destination_display_name(destination: dict[str, Any] | None, destination_id: int) -> str:
    if not destination:
        return f"Destino {destination_id}"
    return (
        destination.get("destination_display_name")
        or destination.get("destination_name")
        or destination.get("destination_label")
        or f"Destino {destination_id}"
    )


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
