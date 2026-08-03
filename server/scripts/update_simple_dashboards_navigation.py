"""Update navigation to expose the simple (Mongo) tactical dashboards.

Agrega los ítems de menú de los informes simples TA12 que consultan Mongo
directamente (sin ETL):

- R2.2  ``/management/rates/calendar``   → Dashboard Tarifas (calendario)
- I1.1  ``/management/service-requests`` → Dashboard Solicitudes

O1.2 (matriz de estado de habitaciones) vive en ``/management/housekeeping/rooms``
y se mejora dentro de esa misma página, por lo que no requiere ítem nuevo.

Idempotente; acepta ``--dry-run``.
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

    # R2.2 — Calendario de tarifas (debajo de "Dashboard ADR" 204.5, sección CRS).
    _upsert(db, "/management/rates/calendar", {
        "label": "Calendario Tarifas",
        "icon": "calendar_month",
        "required_permission": "rates.read",
        "section": "CRS",
        "sort_order": 204.6,
        "is_system": True,
    }, "Calendario Tarifas")

    # I1.1 — Dashboard de solicitudes de servicio (cerca de "Estancias Activas" 210, sección CRS).
    _upsert(db, "/management/service-requests", {
        "label": "Dashboard Solicitudes",
        "icon": "room_service",
        "required_permission": "reservations.read",
        "section": "CRS",
        "sort_order": 210.5,
        "is_system": True,
    }, "Dashboard Solicitudes")

    client.close()


if __name__ == "__main__":
    main()
