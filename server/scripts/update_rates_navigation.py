"""⚠ DEPRECADO (2026-08): el ítem ``/management/rates/dashboard`` (Dashboard
ADR, ``rates.read``, sección CRS, ``sort_order`` 204.5) ya vive en el
``NAVIGATION_CATALOG`` canónico de ``scripts/init_security_model_ga03.py``.

Este script era la fuente paralela que lo insertó directo en la BD. Ahora solo
converge al catálogo canónico vía ``seed_navigation()`` (no-op si la BD ya está
alineada). La fuente única es el catálogo. Acepta ``--dry-run``.

Run: python scripts/update_rates_navigation.py [--dry-run]
"""

from __future__ import annotations

import sys
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from config.settings import get_settings
from pymongo import MongoClient

DRY_RUN = "--dry-run" in sys.argv


def main() -> None:
    settings = get_settings()
    client = MongoClient(settings.mongo_uri)
    db = client[settings.mongo_database]
    try:
        from scripts.init_security_model_ga03 import NAVIGATION_CATALOG, seed_navigation

        print("⚠ DEPRECADO — Dashboard ADR ya vive en NAVIGATION_CATALOG (init_security_model_ga03.py).")
        if DRY_RUN:
            existing = {item["href"] for item in db.navigation.find({}, {"href": 1})}
            missing = [item["href"] for item in NAVIGATION_CATALOG if item["href"] not in existing]
            print(f"  [dry-run] canónico={len(NAVIGATION_CATALOG)} ítems · en BD={len(existing)} · "
                  f"faltantes={missing or 'ninguno'}")
        else:
            seeded = seed_navigation(db["navigation"])
            print(f"  Converged al catálogo canónico: {seeded} ítems nuevos (0 = ya alineado).")
    finally:
        client.close()


if __name__ == "__main__":
    main()
