"""Helpers compartidos del módulo ``etl_status_m2c`` (sin acoplarse a etl_status)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def is_stale_timestamp(value: str | None, *, minutes: int) -> bool:
    parsed = parse_iso_datetime(value)
    if parsed is None:
        return False
    parsed = ensure_utc(parsed)
    return datetime.now(timezone.utc) - parsed > timedelta(minutes=minutes)
