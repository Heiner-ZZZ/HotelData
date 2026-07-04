"""
Ledger hooks: automatically generate double-entry journal entries
from billing events (invoice creation, payment, etc.).
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.database.connection import get_database
from src.app.modules.expenses.service.collections import LEDGER_COLLECTION


def _journal_seq() -> int:
    """Return the next journal entry sequence number."""
    db = get_database()
    last = db[LEDGER_COLLECTION].find_one(
        {"journal_entry_id": {"$regex": "^JE-"}},
        sort=[("journal_entry_id", -1)],
        projection={"journal_entry_id": 1},
    )
    if last:
        try:
            return int(last["journal_entry_id"].split("-")[-1]) + 1
        except (ValueError, IndexError, AttributeError):
            pass
    return 1


def _insert_entry(db, journal_id, tx_date, account_code, account_name, description,
                  debit, credit, cost_center, invoice_ref, booking_id, prop_id, guest_name,
                  source="invoice"):
    db[LEDGER_COLLECTION].insert_one({
        "journal_entry_id": journal_id,
        "entry_type": "auto",
        "tx_date": tx_date,
        "account_code": account_code,
        "account_name": account_name,
        "description": description,
        "debit": round(debit, 2),
        "credit": round(credit, 2),
        "cost_center": cost_center,
        "folio_ref": "",
        "booking_id": booking_id or "",
        "prop_id": int(prop_id) if prop_id else 1,
        "guest_name": guest_name or "",
        "accounting_period": tx_date.strftime("%Y-%m"),
        "source": source,
        "source_id": invoice_ref or "",
        "status": "audited",
        "notes": "",
        "created_at": tx_date,
    })


def generate_ledger_from_invoice(invoice: dict) -> int:
    """Generate double-entry journal entries from an invoice.

    Returns the number of entries created (typically 3-4).

    Accounting logic:
      Debit  1030  AR Huéspedes        ← total (subtotal + taxes)
      Credit 4010  Ingresos Alojamiento ← room_subtotal
      Credit 4030  Ingresos Servicios   ← extras_total (if > 0)
      Credit 2020  Impuestos por Pagar  ← taxes
    """
    db = get_database()

    # Prevent duplicates: check if entries already exist for this invoice
    invoice_ref = invoice.get("invoice_number", "")
    if not invoice_ref:
        return 0

    existing = db[LEDGER_COLLECTION].count_documents({
        "source": "invoice",
        "source_id": invoice_ref,
    })
    if existing > 0:
        return 0

    booking_id = invoice.get("booking_id", "")
    prop_id = invoice.get("prop_id", 0)
    total = float(invoice.get("total", 0) or 0)
    room_subtotal = float(invoice.get("room_subtotal") or 0)
    extras_total = float(invoice.get("extras_total") or 0)
    taxes = float(invoice.get("taxes", 0) or 0)
    subtotal = float(invoice.get("subtotal", 0) or 0)
    issued_at = invoice.get("issued_at")

    # Handle legacy invoices that lack room_subtotal/extras_total fields
    if room_subtotal <= 0 and extras_total <= 0 and subtotal > 0:
        room_subtotal = subtotal
    elif room_subtotal <= 0 and subtotal > extras_total:
        room_subtotal = round(subtotal - extras_total, 2)

    if total <= 0:
        return 0

    tx_date = issued_at if isinstance(issued_at, datetime) else datetime.now(timezone.utc)
    seq = _journal_seq()
    journal_id = f"JE-{tx_date.strftime('%Y%m%d')}-{seq:04d}"

    # Resolve guest name
    guest_name = ""
    if booking_id:
        booking = db.booking_orders.find_one(
            {"booking_id": booking_id},
            {"_id": 0, "guest_name": 1},
        )
        if booking:
            guest_name = booking.get("guest_name", "")

    concept = f"Factura {invoice_ref} — {guest_name or 'Huésped'}"

    # Entry 1: Debit AR
    _insert_entry(
        db, journal_id, tx_date,
        "1030", "Cuentas por Cobrar Huéspedes",
        concept,
        debit=total, credit=0,
        cost_center="Recepción",
        invoice_ref=invoice_ref,
        booking_id=booking_id,
        prop_id=prop_id,
        guest_name=guest_name,
    )

    # Entry 2: Credit Room Revenue
    if room_subtotal > 0:
        _insert_entry(
            db, journal_id, tx_date,
            "4010", "Ingresos por Alojamiento",
            f"Habitación — {concept}",
            debit=0, credit=room_subtotal,
            cost_center="Recepción",
            invoice_ref=invoice_ref,
            booking_id=booking_id,
            prop_id=prop_id,
            guest_name=guest_name,
        )

    # Entry 3: Credit Services Revenue (extras, if any)
    if extras_total > 0:
        _insert_entry(
            db, journal_id, tx_date,
            "4030", "Ingresos por Servicios",
            f"Extras — {concept}",
            debit=0, credit=extras_total,
            cost_center="General",
            invoice_ref=invoice_ref,
            booking_id=booking_id,
            prop_id=prop_id,
            guest_name=guest_name,
        )

    # Entry 4: Credit Taxes Payable
    if taxes > 0:
        _insert_entry(
            db, journal_id, tx_date,
            "2020", "Impuestos por Pagar",
            f"IVA — {concept}",
            debit=0, credit=taxes,
            cost_center="Recepción",
            invoice_ref=invoice_ref,
            booking_id=booking_id,
            prop_id=prop_id,
            guest_name=guest_name,
        )

    entries_count = 1 + (1 if room_subtotal > 0 else 0) + (1 if extras_total > 0 else 0) + (1 if taxes > 0 else 0)
    return entries_count


def generate_reversal_from_invoice(invoice: dict) -> int:
    """Generate reversing double-entry journal entries when an invoice is cancelled.

    This creates the mirror image of the original invoice entries:
      Debit  4010  Ingresos Alojamiento ← room_subtotal (reverses credit)
      Debit  4030  Ingresos Servicios    ← extras_total  (reverses credit)
      Debit  2020  Impuestos por Pagar   ← taxes         (reverses credit)
      Credit 1030  AR Huéspedes         ← total         (reverses debit)

    Returns the number of reversal entries created.
    """
    db = get_database()

    invoice_ref = invoice.get("invoice_number", "")
    if not invoice_ref:
        return 0

    # Prevent duplicate reversals
    existing = db[LEDGER_COLLECTION].count_documents({
        "source": "invoice_reversal",
        "source_id": invoice_ref,
    })
    if existing > 0:
        return 0

    booking_id = invoice.get("booking_id", "")
    prop_id = invoice.get("prop_id", 0)
    total = float(invoice.get("total", 0) or 0)
    room_subtotal = float(invoice.get("room_subtotal") or 0)
    extras_total = float(invoice.get("extras_total") or 0)
    taxes = float(invoice.get("taxes", 0) or 0)
    subtotal = float(invoice.get("subtotal", 0) or 0)

    # Handle legacy invoices that lack room_subtotal/extras_total fields
    if room_subtotal <= 0 and extras_total <= 0 and subtotal > 0:
        room_subtotal = subtotal
    elif room_subtotal <= 0 and subtotal > extras_total:
        room_subtotal = round(subtotal - extras_total, 2)

    if total <= 0:
        return 0

    now = datetime.now(timezone.utc)
    seq = _journal_seq()
    journal_id = f"JE-{now.strftime('%Y%m%d')}-{seq:04d}"

    # Resolve guest name
    guest_name = ""
    if booking_id:
        booking = db.booking_orders.find_one(
            {"booking_id": booking_id},
            {"_id": 0, "guest_name": 1},
        )
        if booking:
            guest_name = booking.get("guest_name", "")

    concept = f"REVERSIÓN Factura {invoice_ref} — {guest_name or 'Huésped'}"

    # Entry 1: Debit Room Revenue (reverses original credit)
    if room_subtotal > 0:
        _insert_entry(
            db, journal_id, now,
            "4010", "Ingresos por Alojamiento",
            f"Reversión habitación — {concept}",
            debit=room_subtotal, credit=0,
            cost_center="Recepción",
            invoice_ref=invoice_ref,
            booking_id=booking_id,
            prop_id=prop_id,
            guest_name=guest_name,
            source="invoice_reversal",
        )

    # Entry 2: Debit Services Revenue (reverses original credit)
    if extras_total > 0:
        _insert_entry(
            db, journal_id, now,
            "4030", "Ingresos por Servicios",
            f"Reversión extras — {concept}",
            debit=extras_total, credit=0,
            cost_center="General",
            invoice_ref=invoice_ref,
            booking_id=booking_id,
            prop_id=prop_id,
            guest_name=guest_name,
            source="invoice_reversal",
        )

    # Entry 3: Debit Taxes Payable (reverses original credit)
    if taxes > 0:
        _insert_entry(
            db, journal_id, now,
            "2020", "Impuestos por Pagar",
            f"Reversión IVA — {concept}",
            debit=taxes, credit=0,
            cost_center="Recepción",
            invoice_ref=invoice_ref,
            booking_id=booking_id,
            prop_id=prop_id,
            guest_name=guest_name,
            source="invoice_reversal",
        )

    # Entry 4: Credit AR (reverses original debit)
    _insert_entry(
        db, journal_id, now,
        "1030", "Cuentas por Cobrar Huéspedes",
        f"Reversión AR — {concept}",
        debit=0, credit=total,
        cost_center="Recepción",
        invoice_ref=invoice_ref,
        booking_id=booking_id,
        prop_id=prop_id,
        guest_name=guest_name,
        source="invoice_reversal",
    )

    entries_count = (1 if room_subtotal > 0 else 0) + (1 if extras_total > 0 else 0) + (1 if taxes > 0 else 0) + 1
    return entries_count


def generate_ledger_from_payment(payment: dict) -> int:
    """Generate double-entry journal entries when a payment is recorded.

    Accounting logic (cash receipt against a guest receivable):
      Debit  1010  Caja / Bancos         ← payment amount
      Credit 1030  Cuentas por Cobrar     ← payment amount (reduces AR)

    Returns the number of entries created (always 2).
    """
    db = get_database()

    payment_ref = payment.get("reference", "")
    if not payment_ref:
        return 0

    # Prevent duplicates
    existing = db[LEDGER_COLLECTION].count_documents({
        "source": "payment",
        "source_id": payment_ref,
    })
    if existing > 0:
        return 0

    booking_id = payment.get("booking_id", "")
    prop_id = payment.get("prop_id", 0)
    amount = float(payment.get("amount", 0) or 0)
    method = payment.get("method", "simulated")
    paid_at = payment.get("paid_at")

    if amount <= 0:
        return 0

    tx_date = paid_at if isinstance(paid_at, datetime) else datetime.now(timezone.utc)
    seq = _journal_seq()
    journal_id = f"JE-{tx_date.strftime('%Y%m%d')}-{seq:04d}"

    # Resolve guest name
    guest_name = ""
    if booking_id:
        booking = db.booking_orders.find_one(
            {"booking_id": booking_id},
            {"_id": 0, "guest_name": 1},
        )
        if booking:
            guest_name = booking.get("guest_name", "")

    method_label = {"simulated": "Simulado", "cash": "Efectivo", "card": "Tarjeta", "transfer": "Transferencia"}.get(method, method.title())
    concept = f"Cobro {payment_ref} ({method_label}) — {guest_name or 'Huésped'}"

    # Entry 1: Debit Cash/Bank
    _insert_entry(
        db, journal_id, tx_date,
        "1010", "Caja / Bancos",
        concept,
        debit=amount, credit=0,
        cost_center="Recepción",
        invoice_ref=payment_ref,
        booking_id=booking_id,
        prop_id=prop_id,
        guest_name=guest_name,
        source="payment",
    )

    # Entry 2: Credit AR (reduces the receivable)
    _insert_entry(
        db, journal_id, tx_date,
        "1030", "Cuentas por Cobrar Huéspedes",
        f"Reducción AR — {concept}",
        debit=0, credit=amount,
        cost_center="Recepción",
        invoice_ref=payment_ref,
        booking_id=booking_id,
        prop_id=prop_id,
        guest_name=guest_name,
        source="payment",
    )

    return 2
