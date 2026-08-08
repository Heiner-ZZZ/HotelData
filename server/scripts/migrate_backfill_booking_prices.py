"""Backfill ``total_price`` for bookings created without a price.

Reservas creadas mientras ``hotel_rate_calendar`` no cubría sus fechas
quedaron con ``total_price=None`` (el path canónico devolvía None sin
tarifas). Esto rompía los emails de notificación (Total "—"), las
penalizaciones de no-show ($0.00) y las facturas ($0.00).

Este script recalcula el precio de TODAS las reservas sin precio con el path
canónico ``_calculate_total_price`` — que ahora cae a
``rate_plans.base_rate`` cuando el calendario no tiene filas — y ``$set``
del precio + campos de tax + metadatos de migración. También recalcula las
penalizaciones de no-show y cancelación que se computaron con el total en
None (quedaron en $0), los folios (``guest_folios``) cuyo posting de
habitación quedó en $0 y las facturas (``reservation_invoices``) que
quedaron con subtotal/taxes/total en $0 (mirror
``fact_reservation_invoices`` incluido).

La operación UNITARIA por reserva vive en
``src.app.modules.reservations.service.pricing_backfill.backfill_single_booking``
— el mismo código que usa ``POST /api/reservations/{booking_id}/recalculate-price``
(el botón "Recalcular precio" de la vista de reservas del admin). Este script
solo orquesta el barrido masivo + reporte; no hay lógica duplicada.

Idempotente: solo toca reservas cuyo ``total_price`` es None/inexistente, y
sella ``metadata.migration_id`` para auditoría. Nunca ``delete_many``.

Usage:
    docker compose -f infra/docker-compose.yml exec -T server \\\\
        python scripts/migrate_backfill_booking_prices.py             # escribe
    docker compose -f infra/docker-compose.yml exec -T server \\\\
        python scripts/migrate_backfill_booking_prices.py --dry-run   # solo reporta
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/app")

from src.app.modules.reservations.service.pricing_backfill import (
    _MISSING_PRICE,
    backfill_single_booking,
    recompute_pending_invoices,
)
from src.database.connection import get_database


def backfill_booking_prices(db, *, dry_run: bool = False) -> dict:
    """Backfill ``total_price`` for bookings without one.

    Returns counts: ``scanned``, ``backfilled``, ``skipped_unpriced``,
    ``penalties_recomputed``, ``folios_recomputed``, ``invoices_recomputed``.
    Cada reserva recalculada se imprime como fila (para el ``--dry-run``).
    """
    now = datetime.now(timezone.utc)
    missing = list(
        db.booking_orders.find(
            _MISSING_PRICE,
            {"_id": 0, "booking_id": 1, "status": 1, "prop_id": 1},
        )
    )

    scanned = 0
    backfilled = 0
    skipped_unpriced = 0
    penalties_recomputed = 0
    folios_recomputed = 0
    invoices_recomputed = 0
    rows: list[tuple[str, str, int, float, int]] = []
    processed_booking_ids: set[str] = set()

    for booking in missing:
        scanned += 1
        booking_id = booking.get("booking_id", "")
        result = backfill_single_booking(db, booking_id, dry_run=dry_run, now=now)
        if result is None:
            continue
        if result.get("already_priced"):
            continue
        if result.get("skipped") == "unpricable":
            skipped_unpriced += 1
            rows.append(
                (booking_id, str(booking.get("status", "")), int(booking.get("prop_id", 0) or 0), 0.0, 0)
            )
            continue

        backfilled += 1
        total = float(result.get("total_price") or 0)
        nights = int(result.get("nights") or 0)
        rows.append(
            (
                booking_id,
                str(result.get("status") or booking.get("status", "")),
                int(result.get("prop_id") or booking.get("prop_id", 0) or 0),
                total,
                nights,
            )
        )
        if result.get("penalty_recomputed"):
            penalties_recomputed += 1
        if result.get("folio_recomputed"):
            folios_recomputed += 1
        if result.get("invoice_recomputed"):
            invoices_recomputed += 1
        if result.get("booking_id"):
            processed_booking_ids.add(str(result["booking_id"]))

    # ── Segundo barrido: facturas en $0 de reservas ya con precio ──────
    # El barrido principal recalcula la factura de las reservas que
    # backfillea ahora. Las facturas rotas de reservas backfilleadas en una
    # corrida anterior (p. ej. la demo INV-202607-0005/0006) se corrigen
    # aquí, reutilizando ``_recompute_invoice`` (misma fórmula canónica y
    # mirror fact_reservation_invoices). ``exclude_booking_ids`` evita el
    # doble conteo en --dry-run de facturas ya contadas por el barrido
    # principal.
    invoices_recomputed += recompute_pending_invoices(
        db,
        exclude_booking_ids=processed_booking_ids,
        dry_run=dry_run,
        now=now,
    )

    # ── Reporte ─────────────────────────────────────────────────────────
    if rows:
        print(f"{'booking_id':<28} {'status':<10} {'prop':>4} {'total':>9} {'nights':>6}")
        print("-" * 62)
        for booking_id, status, prop_id, total, nights in sorted(rows):
            total_str = f"{total:.2f}" if total > 0 else "— (sin tarifa)"
            print(f"{booking_id:<28} {status:<10} {prop_id:>4} {total_str:>9} {nights:>6}")

    print(
        f"\n[backfill_booking_prices] scanned={scanned} backfilled={backfilled} "
        f"skipped_unpriced={skipped_unpriced} "
        f"penalties_recomputed={penalties_recomputed} "
        f"folios_recomputed={folios_recomputed} "
        f"invoices_recomputed={invoices_recomputed} "
        f"({'DRY-RUN — sin escrituras' if dry_run else 'escrituras aplicadas'})"
    )
    return {
        "scanned": scanned,
        "backfilled": backfilled,
        "skipped_unpriced": skipped_unpriced,
        "penalties_recomputed": penalties_recomputed,
        "folios_recomputed": folios_recomputed,
        "invoices_recomputed": invoices_recomputed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backfill total_price for bookings created without a price."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would change without writing to the database.",
    )
    args = parser.parse_args()

    db = get_database()
    backfill_booking_prices(db, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
