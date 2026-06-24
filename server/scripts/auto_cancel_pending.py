#!/usr/bin/env python3
"""Auto-cancel pending bookings older than 24 hours.

Usage:
    python scripts/auto_cancel_pending.py

Can be scheduled via cron, e.g.:
    0 * * * * cd /opt/hoteldata && python scripts/auto_cancel_pending.py >> data/logs/auto_cancel.log 2>&1
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

# Ensure the project root is in sys.path so imports work
# Script is at: {project_root}/server/scripts/auto_cancel_pending.py
# Project root is 3 levels up from the script
_script_dir = Path(__file__).resolve().parent
PROJECT_ROOT = Path(os.getenv("HOTELDATA_PROJECT_ROOT", str(_script_dir.parent.parent)))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.app.modules.reservations.service.cleanup import auto_cancel_expired_pending


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("auto_cancel_script")


def main() -> int:
    logger.info("Starting auto-cancel of expired pending bookings...")
    try:
        result = auto_cancel_expired_pending()
        cancelled = result.get("cancelled", 0)
        expired_found = result.get("expired_count", 0)
        errors = result.get("errors", [])
        logger.info(
            "Auto-cancel complete: %d expired found, %d cancelled, %d errors",
            expired_found, cancelled, len(errors),
        )
        if errors:
            for err in errors:
                logger.warning("  Error: %s", err)
        return 0 if not errors else 1
    except Exception as exc:
        logger.exception("Auto-cancel failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
