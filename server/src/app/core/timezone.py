"""Centralized timezone utilities.

Reads the TZ environment variable (default: "UTC") and provides
``local_now()`` and ``local_today()`` helpers so that date‑boundary
comparisons respect the hotel's local timezone instead of always
using UTC.

Usage::

    from src.app.core.timezone import local_now, local_today

    if check_out_date < local_today():
        # check‑out has passed in the hotel's local timezone
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore[no-redef]


def _get_tz_name() -> str:
    """Read the timezone name from environment, defaulting to UTC."""
    return os.getenv("TZ", "UTC").strip()


def _get_zoneinfo() -> ZoneInfo:
    """Return a ZoneInfo for the configured timezone.

    Falls back to UTC if the name is invalid.
    """
    name = _get_tz_name()
    try:
        return ZoneInfo(name)
    except Exception:  # nosec
        return ZoneInfo("UTC")


def local_now() -> datetime:
    """Return the current datetime in the configured timezone."""
    return datetime.now(timezone.utc).astimezone(_get_zoneinfo())


def local_today() -> str:
    """Return today's date string (YYYY-MM-DD) in the configured timezone."""
    return local_now().strftime("%Y-%m-%d")


def utc_now() -> datetime:
    """Return the current datetime in UTC (backward‑compatible alias)."""
    return datetime.now(timezone.utc)
