"""Repair: cancel empty $0 invoices created for bookings without a price.

Causa raíz: el checkout emitía facturas con ``total`` en cero cuando la reserva
no tenía ``total_price`` (ni line items). Esas facturas vacías no tienen valor
fiscal y contaminan los KPIs tácticos (F1.4/F1.5). Este script las anula en
``reservation_invoices`` y ``fact_reservation_invoices`` (espejo).

Es one-shot e idempotente: acepta ``--dry-run`` para simular, ``--prop-id`` para
acotar a una propiedad y ``--max`` para limitar el alcance por corrida.
Las facturas ya anuladas no se tocan.
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

INVOICES = "reservation_invoices"
FACT_INVOICES = "fact_reservation_invoices"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    prop_id: int | None = None
    if "--prop-id" in sys.argv:
        prop_id = int(sys.argv[sys.argv.index("--prop-id") + 1])
    max_cancel = 500
    if "--max" in sys.argv:
        max_cancel = int(sys.argv[sys.argv.index("--max") + 1])

    settings = get_settings()
    client = MongoClient(settings.mongo_uri)
    db = client[settings.mongo_database]

    query: dict = {
        "status": {"$ne": "cancelled"},
        # ``{"total": None}`` ya cubre null y campo ausente en Mongo.
        "$or": [{"total": {"$lte": 0}}, {"total": None}],
    }
    if prop_id is not None:
        query["prop_id"] = prop_id
    scope = f"prop_id={prop_id}" if prop_id is not None else "TODOS LOS HOTELES"
    print(f"[alcance] {scope}")

    candidates = list(
        db[INVOICES].find(
            query,
            {"invoice_number": 1, "booking_id": 1, "prop_id": 1, "status": 1, "total": 1, "line_items": 1},
        ).limit(max_cancel)
    )
    # Solo facturas realmente vacías: sin line items con importe. No se anulan
    # facturas con conceptos aunque el total quede en cero (p.ej. 100% descuento).
    empty = [
        doc for doc in candidates
        if not [it for it in (doc.get("line_items") or []) if float((it or {}).get("total", 0) or 0) > 0]
    ]

    if not empty:
        print("Sin facturas vacías en $0 por anular.")
        client.close()
        return

    print(f"[{'DRY-RUN' if dry_run else 'APPLY'}] {len(empty)} factura(s) vacía(s) en $0:")
    for doc in empty:
        print(
            f"  - {doc.get('invoice_number', '?')} "
            f"prop={doc.get('prop_id')} status={doc.get('status')} "
            f"total={doc.get('total')} booking={doc.get('booking_id', '')}"
        )

    if dry_run:
        print("Sin cambios aplicados (--dry-run).")
        client.close()
        return

    stamp = {"status": "cancelled", "cancelled_at": utc_now(), "updated_at": utc_now()}
    cancelled = 0
    for doc in empty:
        doc_id = doc["_id"]
        for collection in (INVOICES, FACT_INVOICES):
            result = db[collection].update_one(
                {"_id": doc_id, "status": {"$ne": "cancelled"}},
                {"$set": {**stamp, "repair_metadata": {"script": "repair_zero_invoices", "at": utc_now()}}},
            )
            if result.matched_count:
                cancelled += 1
    updated = len(empty)
    print(f"Anuladas {updated} factura(s) × 2 colecciones = {cancelled} actualización(es).")
    client.close()


if __name__ == "__main__":
    main()
