"""Update the Billing navigation section to add the F1.4 Dashboard item.

Histórico: este script eliminó el ítem redundante "Facturas" (duplicado del
header) y creó "Pagos". Ahora además garantiza el ítem ``/management/billing/dashboard``
para el informe táctico F1.4. Es idempotente; acepta ``--dry-run``.
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

    # Ensure the "Facturación" header still exists.
    _upsert(db, "/management/billing", {
        "label": "Facturación",
        "icon": "receipt",
        "required_permission": "billing.read",
        "section": "Billing",
        "is_section_header": True,
        "sort_order": 503,
        "is_system": True,
    }, "Facturación header")

    # Dashboard táctico F1.4 (debajo del header, antes de Pagos).
    # El backend ordena por ``sort_order`` numérico ascendente, así que
    # Dashboard=504, Dashboard Pagos=505 y Pagos=506 mantienen el orden deseado.
    _upsert(db, "/management/billing/dashboard", {
        "label": "Dashboard",
        "icon": "monitoring",
        "required_permission": "billing.read",
        "section": "Billing",
        "sort_order": 504,
        "is_system": True,
    }, "Dashboard")

    # Dashboard táctico F1.5 (pagos por método y saldo pendiente).
    _upsert(db, "/management/billing/payments-dashboard", {
        "label": "Dashboard Pagos",
        "icon": "payments",
        "required_permission": "payments.read",
        "section": "Billing",
        "sort_order": 505,
        "is_system": True,
    }, "Dashboard Pagos")

    # Upsert the "Pagos" item under the Billing section.
    _upsert(db, "/management/billing/payments", {
        "label": "Pagos",
        "icon": "payments",
        "required_permission": "payments.read",
        "section": "Billing",
        "sort_order": 506,
        "is_system": True,
    }, "Pagos")

    client.close()


if __name__ == "__main__":
    main()
