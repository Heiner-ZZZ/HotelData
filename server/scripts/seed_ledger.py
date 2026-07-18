"""
Generate real double-entry ledger transactions from guest_folios postings.
Each folio posting produces 2 journal entries (debit + credit).

Run: docker compose exec server python -m scripts.seed_ledger
"""
from datetime import datetime, timezone

from src.database.connection import get_database
from src.app.modules.expenses.service.collections import LEDGER_COLLECTION

# ═══ Posting type → (debit_account, credit_account, cost_center) ═══
POSTING_ACCOUNT_MAP = {
    "room": {
        "Habitación": ("1030", "Cuentas por Cobrar Huéspedes", "4010", "Ingresos por Alojamiento", "Recepción"),
    },
    "charge": {
        "Restaurante": ("1030", "Cuentas por Cobrar Huéspedes", "4020", "Ingresos por Alimentos y Bebidas", "Alimentos y Bebidas"),
        "Bar": ("1030", "Cuentas por Cobrar Huéspedes", "4020", "Ingresos por Alimentos y Bebidas", "Alimentos y Bebidas"),
        "Room Service": ("1030", "Cuentas por Cobrar Huéspedes", "4020", "Ingresos por Alimentos y Bebidas", "Alimentos y Bebidas"),
        "Minibar": ("1030", "Cuentas por Cobrar Huéspedes", "4020", "Ingresos por Alimentos y Bebidas", "Alimentos y Bebidas"),
        "Spa": ("1030", "Cuentas por Cobrar Huéspedes", "4030", "Ingresos por Servicios", "Spa"),
        "Lavandería": ("1030", "Cuentas por Cobrar Huéspedes", "4030", "Ingresos por Servicios", "Lavandería"),
        "Parking": ("1030", "Cuentas por Cobrar Huéspedes", "4030", "Ingresos por Servicios", "Estacionamiento"),
        "Llamadas": ("1030", "Cuentas por Cobrar Huéspedes", "4030", "Ingresos por Servicios", "General"),
        "Mascotas": ("1030", "Cuentas por Cobrar Huéspedes", "4030", "Ingresos por Servicios", "General"),
        "Daños": ("1030", "Cuentas por Cobrar Huéspedes", "4040", "Otros Ingresos Operativos", "General"),
        "Late Check-Out": ("1030", "Cuentas por Cobrar Huéspedes", "4040", "Otros Ingresos Operativos", "Recepción"),
        "Otros": ("1030", "Cuentas por Cobrar Huéspedes", "4040", "Otros Ingresos Operativos", "General"),
    },
    "payment": {
        "_default": ("1010", "Caja General", "1030", "Cuentas por Cobrar Huéspedes", "Recepción"),
    },
    "discount": {
        "_default": ("6010", "Descuentos por Promoción", "1030", "Cuentas por Cobrar Huéspedes", "Recepción"),
    },
    "adjustment": {
        "_default": ("6020", "Ajustes por Cortesía", "1030", "Cuentas por Cobrar Huéspedes", "Recepción"),
    },
}


def _resolve_accounts(posting_type: str, category: str) -> tuple | None:
    """Return (debit_code, debit_name, credit_code, credit_name, cost_center) or None."""
    type_map = POSTING_ACCOUNT_MAP.get(posting_type)
    if not type_map:
        return None

    if posting_type in ("payment", "discount", "adjustment"):
        return type_map["_default"]

    # For 'room' and 'charge', look up by category
    cat_map = type_map.get(category)
    if cat_map:
        return cat_map

    # Fallback: treat unknown charge categories as "Otros"
    fallback = type_map.get("Otros")
    if fallback:
        return fallback

    return None


def _generate_journal_id(seq: int) -> str:
    return f"JE-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{seq:04d}"


def seed():
    db = get_database()
    existing = db[LEDGER_COLLECTION].count_documents({})
    if existing > 0:
        print(f"[CLEAR] Removing {existing} old hardcoded ledger entries...")
        db[LEDGER_COLLECTION].delete_many({})

    folios = list(db.guest_folios.find().sort("created_at", 1))
    if not folios:
        print("[SKIP] No guest_folios found — nothing to generate from")
        return

    journal_seq = 0
    total_entries = 0

    for folio in folios:
        folio_number = folio.get("folio_number", "")
        booking_id = folio.get("booking_id", "")
        prop_id = folio.get("prop_id", 0)
        guest_name = folio.get("guest_name", "")
        postings = folio.get("postings", [])

        for posting in postings:
            ptype = posting.get("type", "charge")
            category = posting.get("category", "Otros")
            concept = posting.get("concept", "")
            amount = float(posting.get("amount", 0) or 0)
            posted_at = posting.get("posted_at")

            if amount <= 0 or not posted_at:
                continue

            accounts = _resolve_accounts(ptype, category)
            if not accounts:
                continue

            debit_code, debit_name, credit_code, credit_name, cost_center = accounts
            journal_seq += 1
            journal_id = _generate_journal_id(journal_seq)

            tx_date = posted_at if isinstance(posted_at, datetime) else datetime.now(timezone.utc)
            accounting_period = tx_date.strftime("%Y-%m")

            # Entry 1: DEBIT
            db[LEDGER_COLLECTION].insert_one({
                "journal_entry_id": journal_id,
                "entry_type": "auto",
                "tx_date": tx_date,
                "account_code": debit_code,
                "account_name": debit_name,
                "description": f"{concept} [{guest_name}]",
                "debit": round(amount, 2),
                "credit": 0.0,
                "cost_center": cost_center,
                "folio_ref": folio_number,
                "booking_id": booking_id,
                "prop_id": int(prop_id) if prop_id else 1,
                "guest_name": guest_name,
                "accounting_period": accounting_period,
                "source": "folio_posting",
                "source_id": str(posting.get("posting_id", "")),
                "status": "audited",
                "notes": "",
                "created_at": tx_date,
            })

            # Entry 2: CREDIT
            db[LEDGER_COLLECTION].insert_one({
                "journal_entry_id": journal_id,
                "entry_type": "auto",
                "tx_date": tx_date,
                "account_code": credit_code,
                "account_name": credit_name,
                "description": f"{concept} [{guest_name}]",
                "debit": 0.0,
                "credit": round(amount, 2),
                "cost_center": cost_center,
                "folio_ref": folio_number,
                "booking_id": booking_id,
                "prop_id": int(prop_id) if prop_id else 1,
                "guest_name": guest_name,
                "accounting_period": accounting_period,
                "source": "folio_posting",
                "source_id": str(posting.get("posting_id", "")),
                "status": "audited",
                "notes": "",
                "created_at": tx_date,
            })

            total_entries += 2

    print(f"[OK] Generated {total_entries} double-entry ledger transactions from {len(folios)} guest folios ({journal_seq} journal entries)")

    # Also generate from existing reservation_invoices
    invoice_entries = 0
    invoices = list(db.reservation_invoices.find())
    if invoices:
        from src.app.modules.expenses.service.ledger_hooks import generate_ledger_from_invoice
        for inv in invoices:
            n = generate_ledger_from_invoice(inv)
            invoice_entries += n
        print(f"[OK] Generated {invoice_entries} ledger entries from {len(invoices)} reservation invoices")

    print(f"[DONE] Total ledger entries: {total_entries + invoice_entries}")


if __name__ == "__main__":
    seed()
