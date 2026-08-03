"""Update the CRS navigation section to add the R1.2 ADR Dashboard item.

Crea (idempotente) el ítem ``/management/rates/dashboard`` bajo la sección
CRS para el informe táctico R1.2 (ADR por fecha, tipo de habitación y canal).
El backend ordena por ``sort_order`` numérico ascendente; usamos 204.5 para
quedar inmediatamente después de Tarifas (204) y antes de Propiedades (205)
sin recolocar los ítems existentes.

Uso:
    python server/scripts/update_rates_navigation.py            # aplica
    python server/scripts/update_rates_navigation.py --dry-run  # simula
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parents[1]
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from config.settings import get_settings
from pymongo import MongoClient


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _upsert(db, href: str, patch: dict, label: str) -> None:
    """Aplica (o simula con --dry-run) un upsert idempotente de navegación."""
    existing = db.navigation.find_one({"href": href}, {"_id": 1})
    action = "would upsert" if DRY_RUN else "upserting"
    if existing:
        action = "would update" if DRY_RUN else "updating"
    print(f"[{action}] {label} ({href})")
    if DRY_RUN:
        return
    result = db.navigation.update_one(
        {"href": href},
        {
            "$set": {**patch, "updated_at": utc_now()},
            "$setOnInsert": {"created_at": utc_now()},
        },
        upsert=True,
    )
    print(f"  matched={result.matched_count}, upserted={result.upserted_id is not None}")


DRY_RUN = "--dry-run" in sys.argv


def main() -> None:
    settings = get_settings()
    client = MongoClient(settings.mongo_uri)
    db = client[settings.mongo_database]

    # Dashboard táctico R1.2 (ADR) dentro de la sección CRS, justo después de
    # Tarifas (204). El backend ordena por sort_order ascendente.
    _upsert(db, "/management/rates/dashboard", {
        "label": "Dashboard ADR",
        "icon": "monitoring",
        "required_permission": "rates.read",
        "section": "CRS",
        "sort_order": 204.5,
        "is_system": True,
    }, "Dashboard ADR")

    client.close()


if __name__ == "__main__":
    main()
