"""Manual smoke test: create a payment and verify ledger entries.

This file is a runnable diagnostic, not a pytest module.  Keeping all database
work behind ``main`` prevents pytest's recursive discovery from writing to a
real database or aborting collection when the database has no bookings.
"""
from __future__ import annotations


def main() -> int:
    from src.database.connection import get_database
    from src.app.modules.billing.schemas import PaymentCreate
    from src.app.modules.billing.service.lifecycle.payments import create_payment

    db = get_database()

    # Find any booking
    booking = db.booking_orders.find_one({})
    if not booking:
        print("No bookings found; smoke test skipped")
        return 0

    booking_id = booking.get("booking_id", "")
    print(f"Booking: {booking_id}")

    # Create a test payment
    payload = PaymentCreate(
        booking_id=booking_id,
        invoice_id="",
        amount=150.00,
        method="card",
    )
    result = create_payment(payload)
    if result:
        ref = result.get("reference", "")
        print(f"Payment: {ref} | amount={result.get('amount')} | status={result.get('status')}")

        # Verify ledger entries
        entries = list(db.ledger_transactions.find({"source": "payment", "source_id": ref}))
        print(f"Ledger entries: {len(entries)}")
        total_d = sum(e.get("debit", 0) for e in entries)
        total_c = sum(e.get("credit", 0) for e in entries)
        print(f"Debits: {total_d:.2f}, Credits: {total_c:.2f}, Balanced: {abs(total_d - total_c) < 0.01}")
        for entry in entries:
            print(
                f"  {entry.get('account_code')} {entry.get('account_name')} "
                f"| D:{entry.get('debit')} C:{entry.get('credit')} "
                f"| source={entry.get('source')}"
            )
        return 0 if len(entries) == 2 and abs(total_d - total_c) < 0.01 else 1

    print("Payment creation failed")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
