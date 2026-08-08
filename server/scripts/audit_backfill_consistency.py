"""Audit report — post-backfill consistency of booking↔folio↔invoice.

Reporte SOLO-lectura (nunca escribe) que lista cada reserva con su folio y
factura, y detecta inconsistencias restantes tras el backfill de precios
(``migrate_backfill_booking_prices.py``). Pensado para auditar la demo
completa y cualquier entorno antes/después de migraciones.

Categorías de hallazgos (``report["issues"]``):

- ``folio_room_zero`` — el folio tiene un posting de habitación en $0 pero la
  reserva tiene ``total_price > 0``. El backfill de folios solo corrige este
  estado cuando backfillea la reserva en la MISMA corrida; el caso de la demo
  (``FL-202607-0003``) es una reserva YA con precio que quedó con room $0.
- ``invoice_zero`` — la factura tiene ``total`` en 0/ausente y la reserva
  tiene precio. (El barrido de facturas pendientes la corrige; esto detecta
  las que queden.) NOTA: una factura anulada legítimamente en $0
  (cancelled/refunded) también aparece aquí — es intencional, porque son
  las facturas rotas que el barrido re-preció; revisar el estado antes de
  descartarlo.

El reporte también incluye ``bookings_summary``: la tabla cross-reference de
TODAS las reservas (booking → folio → invoice), con ``consistent`` = True
cuando la reserva tiene folio, factura y montos coherentes.
- ``due_invoice_mismatch`` — el folio ``total_due`` y ``invoice.total``
  difieren en más de 1.00 cuando ambos existen y tienen montos reales.
  Señala divergencia entre la cuenta viva y la factura emitida (p. ej. el
  folio acumuló cargos que la factura no refleja, o viceversa).
- ``folio_expired_open`` — folio ``status=open`` cuyo ``check_out_date`` ya
  pasó (el cleanup automático no lo cerró).
- ``orphan_folio`` / ``orphan_invoice`` — el documento referencia un
  ``booking_id`` inexistente.
- ``missing_folio`` / ``missing_invoice`` — reserva operativa (no
  cancelled/rejected) sin folio o sin factura. INFORMATIVO: no es un error
  (p. ej. una reserva confirmada aún no hizo check-in no tiene folio).

Uso:
    docker compose -f infra/docker-compose.yml exec -T server \\
        python scripts/audit_backfill_consistency.py              # toda la BD
    ... --prop-id 1                                               # solo un hotel
    ... --today 2026-08-10                                        # fijar "hoy"

Exit code: 0 si no hay hallazgos que requieran acción (los missing_* no
cuentan), 1 si hay inconsistencias reales (folio_room_zero, invoice_zero,
due_invoice_mismatch, folio_expired_open, orphans).
"""
from __future__ import annotations

import argparse
import sys
from typing import Any

sys.path.insert(0, "/app")

from src.database.connection import get_database

# Umbral de divergencia folio.total_due vs invoice.total que se considera
# inconsistencia (dólares).
DUE_INVOICE_TOLERANCE = 1.00

# Estados que no generan missing_folio / missing_invoice (no operativas).
SKIP_MISSING_STATUSES = {"cancelled", "rejected"}

# Categorías que hacen que el exit code sea 1 (requieren acción).
ACTIONABLE_CATEGORIES = {
    "folio_room_zero",
    "invoice_zero",
    "due_invoice_mismatch",
    "folio_expired_open",
    "orphan_folio",
    "orphan_invoice",
}


def audit_consistency(db, *, today: str | None = None, prop_id: int | None = None) -> dict[str, Any]:
    """Auditar booking↔folio↔invoice en toda la BD (o un hotel).

    Returns:
        {
          "total_bookings": int,
          "prop_id": int | None,
          "issues": [{"category": str, ...}, ...],
          "counts": {category: int},
          "bookings_summary": [{"booking_id": str, "folio_number": ...,
                                "invoice_number": ..., "consistent": bool}, ...],
        }

    Es SOLO lectura — nunca escribe.
    """
    from src.app.core.timezone import local_today

    today = today or local_today()

    booking_query: dict[str, Any] = {}
    folio_query: dict[str, Any] = {}
    invoice_query: dict[str, Any] = {}
    if prop_id is not None:
        booking_query["prop_id"] = prop_id
        folio_query["prop_id"] = prop_id
        invoice_query["prop_id"] = prop_id

    issues: list[dict[str, Any]] = []
    counts: dict[str, int] = {}

    def add_issue(category: str, **fields: Any) -> None:
        issues.append({"category": category, **fields})
        counts[category] = counts.get(category, 0) + 1

    # ── Índices en memoria: booking por id ──
    bookings = {
        b["booking_id"]: b
        for b in db.booking_orders.find(
            booking_query, {"_id": 0, "booking_id": 1, "status": 1, "total_price": 1}
        )
    }
    total_bookings = len(bookings)

    # ── Folios ──
    folios = list(
        db.guest_folios.find(
            folio_query,
            {
                "_id": 0,
                "folio_number": 1, "booking_id": 1, "status": 1,
                "check_out_date": 1, "total_room": 1, "total_charges": 1,
                "total_discounts": 1, "total_payments": 1, "total_due": 1,
                "postings": 1,
            },
        )
    )

    # ── Facturas ──
    invoices = list(
        db.reservation_invoices.find(
            invoice_query,
            {
                "_id": 0,
                "invoice_number": 1, "booking_id": 1, "status": 1,
                "subtotal": 1, "taxes": 1, "total": 1,
            },
        )
    )

    folio_by_booking: dict[str, list[dict]] = {}
    for folio in folios:
        folio_by_booking.setdefault(folio.get("booking_id") or "", []).append(folio)

    invoice_by_booking: dict[str, list[dict]] = {}
    for invoice in invoices:
        invoice_by_booking.setdefault(invoice.get("booking_id") or "", []).append(invoice)

    # ── Orphans: folio/invoice sin booking ──
    for folio in folios:
        bid = folio.get("booking_id") or ""
        if bid and bid not in bookings:
            add_issue(
                "orphan_folio",
                folio_number=folio.get("folio_number", ""),
                booking_id=bid,
            )
    for invoice in invoices:
        bid = invoice.get("booking_id") or ""
        if bid and bid not in bookings:
            add_issue(
                "orphan_invoice",
                invoice_number=invoice.get("invoice_number", ""),
                booking_id=bid,
            )

    # ── Tabla cross-reference: booking → folio → invoice ──
    # Lista TODAS las reservas (happy path incluido), con el folio/factura
    # de cada una. El CLI la imprime como tabla resumen; ``consistent`` es
    # True cuando la reserva tiene folio, factura y montos coherentes.
    bookings_summary: list[dict[str, Any]] = []
    for booking_id in sorted(bookings):
        booking_folios = folio_by_booking.get(booking_id, [])
        booking_invoices = invoice_by_booking.get(booking_id, [])
        folio = booking_folios[0] if booking_folios else None
        invoice = booking_invoices[0] if booking_invoices else None
        folio_due = float((folio or {}).get("total_due", 0) or 0)
        invoice_total = float((invoice or {}).get("total", 0) or 0)
        consistent = bool(
            folio
            and invoice
            and folio_due > 0
            and invoice_total > 0
            and abs(folio_due - invoice_total) <= DUE_INVOICE_TOLERANCE
        )
        bookings_summary.append(
            {
                "booking_id": booking_id,
                "status": bookings[booking_id].get("status", ""),
                "folio_number": (folio or {}).get("folio_number"),
                "folio_status": (folio or {}).get("status"),
                "folio_due": folio_due,
                "invoice_number": (invoice or {}).get("invoice_number"),
                "invoice_status": (invoice or {}).get("status"),
                "invoice_total": invoice_total,
                "consistent": consistent,
            }
        )

    # ── Por reserva operativa ──
    for booking_id, booking in bookings.items():
        booking_folios = folio_by_booking.get(booking_id, [])
        booking_invoices = invoice_by_booking.get(booking_id, [])
        status = booking.get("status", "")
        booking_total = float(booking.get("total_price", 0) or 0)

        # Missing (informativo): reserva operativa sin folio/factura.
        if status not in SKIP_MISSING_STATUSES:
            if not booking_folios:
                add_issue("missing_folio", booking_id=booking_id, status=status)
            if not booking_invoices:
                add_issue("missing_invoice", booking_id=booking_id, status=status)

        # Folio room $0 con reserva con precio.
        if booking_total > 0:
            for folio in booking_folios:
                room_posting = next(
                    (
                        p
                        for p in (folio.get("postings") or [])
                        if p.get("type") == "room"
                        and p.get("reference_type") == "booking"
                    ),
                    None,
                )
                if room_posting is not None and float(room_posting.get("amount", 0) or 0) == 0:
                    add_issue(
                        "folio_room_zero",
                        booking_id=booking_id,
                        folio_number=folio.get("folio_number", ""),
                        total_room=float(folio.get("total_room", 0) or 0),
                        booking_total=booking_total,
                    )

        # Invoice en $0 con reserva con precio.
        if booking_total > 0:
            for invoice in booking_invoices:
                inv_total = float(invoice.get("total", 0) or 0)
                if inv_total == 0:
                    add_issue(
                        "invoice_zero",
                        booking_id=booking_id,
                        invoice_number=invoice.get("invoice_number", ""),
                        status=invoice.get("status", ""),
                    )

        # total_due vs invoice.total.
        # - Folio OPEN: la cuenta viva aún puede divergir de la factura.
        # - Folio CLOSED con total_due > 0: se cerró con deuda pendiente — un
        #   folio correctamente liquidado cierra en 0 (los pagos lo reducen).
        #   Si además hay factura con monto real, la divergencia es señal de
        #   que el folio acumuló cargos que la factura no refleja (caso demo
        #   FL-202607-0003 due=283 vs factura paid=92.80).
        for folio in booking_folios:
            folio_due = float(folio.get("total_due", 0) or 0)
            is_open = folio.get("status") == "open"
            is_closed_with_debt = folio.get("status") == "closed" and folio_due > 0
            if not (is_open or is_closed_with_debt):
                continue
            for invoice in booking_invoices:
                inv_total = float(invoice.get("total", 0) or 0)
                inv_status = invoice.get("status", "")
                if inv_total <= 0 or inv_status in ("cancelled", "refunded"):
                    continue
                diff = round(folio_due - inv_total, 2)
                if abs(diff) > DUE_INVOICE_TOLERANCE:
                    add_issue(
                        "due_invoice_mismatch",
                        booking_id=booking_id,
                        folio_number=folio.get("folio_number", ""),
                        invoice_number=invoice.get("invoice_number", ""),
                        folio_due=folio_due,
                        invoice_total=inv_total,
                        diff=diff,
                    )

        # Folio open cuyo check_out ya pasó.
        for folio in booking_folios:
            if folio.get("status") != "open":
                continue
            check_out = str(folio.get("check_out_date", "") or "")[:10]
            if check_out and check_out < today:
                add_issue(
                    "folio_expired_open",
                    booking_id=booking_id,
                    folio_number=folio.get("folio_number", ""),
                    check_out_date=check_out,
                    total_due=float(folio.get("total_due", 0) or 0),
                )

    return {
        "total_bookings": total_bookings,
        "prop_id": prop_id,
        "today": today,
        "issues": issues,
        "counts": counts,
        "bookings_summary": bookings_summary,
    }


# ── CLI ──────────────────────────────────────────────────────────────────


def _print_report(report: dict[str, Any]) -> int:
    counts = report["counts"]
    print("=" * 76)
    print("AUDITORÍA POST-BACKFILL — consistencia booking ↔ folio ↔ invoice")
    print("=" * 76)
    scope = f"prop_id={report['prop_id']}" if report.get("prop_id") else "TODA la BD"
    print(f"Alcance: {scope} | Reservas: {report['total_bookings']} | hoy: {report['today']}")
    print()

    # ── Tabla cross-reference booking → folio → invoice ──
    print("── Reservas (booking → folio → invoice) ──")
    print(
        f"{'booking_id':<28} {'status':<10} {'folio':<16} {'folio_status':<8} "
        f"{'folio_due':>9} {'invoice':<16} {'inv_status':<9} {'inv_total':>9} {'ok':>4}"
    )
    print("-" * 115)
    for row in report.get("bookings_summary", []):
        print(
            f"{row['booking_id']:<28} {row['status']:<10} "
            f"{row['folio_number'] or '—'!s:<16} {row['folio_status'] or '—'!s:<8} "
            f"{row['folio_due']:>9.2f} {row['invoice_number'] or '—'!s:<16} "
            f"{row['invoice_status'] or '—'!s:<9} {row['invoice_total']:>9.2f} "
            f"{'✓' if row['consistent'] else '✗':>4}"
        )
    print()

    if not report["issues"]:
        print("✅ Sin hallazgos. Todo consistente.")
        return 0

    grouped: dict[str, list[dict]] = {}
    for issue in report["issues"]:
        grouped.setdefault(issue["category"], []).append(issue)

    for category, items in sorted(grouped.items()):
        print(f"── {category} ({len(items)}) ──")
        for item in items:
            detail = " | ".join(
                f"{k}={v}" for k, v in item.items() if k != "category"
            )
            print(f"   {detail}")
        print()

    print("-" * 76)
    for category, count in sorted(counts.items()):
        print(f"  {category:<22} {count}")
    print("-" * 76)

    actionable = sum(counts.get(c, 0) for c in ACTIONABLE_CATEGORIES)
    informative = sum(
        count for cat, count in counts.items() if cat not in ACTIONABLE_CATEGORIES
    )
    print(f"Accionables: {actionable} | Informativos (missing_*): {informative}")
    return 1 if actionable > 0 else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prop-id", type=int, default=None, help="Filtrar por hotel.")
    parser.add_argument("--today", type=str, default=None, help="Fijar 'hoy' (YYYY-MM-DD).")
    args = parser.parse_args(argv)

    db = get_database()
    report = audit_consistency(db, today=args.today, prop_id=args.prop_id)
    return _print_report(report)


if __name__ == "__main__":
    sys.exit(main())
