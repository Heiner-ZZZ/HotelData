"""Per-booking price backfill — admin "Recalcular precio" tooling.

Una reserva creada mientras ``hotel_rate_calendar`` no cubría sus fechas
quedó con ``total_price=None`` (el path canónico devolvía None sin tarifas).
Esto rompía los emails de notificación (Total "—"), las penalizaciones de
no-show ($0.00) y las facturas ($0.00).

Este módulo expone la operación UNITARIA reutilizada por:

- ``POST /api/reservations/{booking_id}/recalculate-price`` (endpoint del
  banner "reservas sin precio" en la vista de reservas del admin).
- ``scripts/migrate_backfill_booking_prices.py`` (backfill masivo de la demo).

El cálculo usa el path canónico ``_calculate_total_price`` — que ahora cae a
``rate_plans.base_rate`` cuando el calendario no tiene filas — y $set del
precio + campos de tax + metadatos de migración. También recalcula las
penalizaciones de no-show/cancelación que quedaron en $0 (mirror de
``no_show.py`` / ``cleanup.py``) y los folios cuyo posting de habitación
quedó en $0 (mirror de ``folio.create_folio``).

Idempotente: reservas ya con precio → ``already_priced`` (no-op). Reservas
sin tarifa calculable → ``skipped=unpricable`` (no escribe). Nunca
``delete_many``; solo ``$set``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.app.modules.reservations.service import resolve_penalty_percent
from src.app.modules.reservations.service.lifecycle.create._pricing import (
    _calculate_total_price,
)
from src.app.security.hotel_filter import hotel_filter_from_user

MIGRATION_ID = "backfill_booking_prices_v1"

_MISSING_PRICE = {
    "$or": [
        {"total_price": {"$exists": False}},
        {"total_price": None},
    ]
}


def list_unpriced_bookings(
    db,
    *,
    user: dict[str, Any] | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Bookings sin ``total_price``, respetando el filtro de hoteles del user.

    Solo staff con ``reservations.update`` debería llamar esto (la vista de
    mantenimiento del admin); el filtro de hotel se aplica igual que en
    ``list_bookings`` (``hotel_filter_from_user``) para que un gerente solo
    vea las reservas sin precio de SUS hoteles.
    """
    filters: dict[str, Any] = dict(_MISSING_PRICE)
    user_filter = hotel_filter_from_user(user)
    if user_filter:
        filters.update(user_filter)
    items = list(
        db.booking_orders.find(
            filters,
            {
                "_id": 0,
                "booking_id": 1, "prop_id": 1, "status": 1,
                "guest_name": 1, "check_in_date": 1, "check_out_date": 1,
                "total_nights": 1, "currency": 1, "created_at": 1,
            },
        )
        .sort([("created_at", -1)])
        .limit(limit)
    )
    for item in items:
        if isinstance(item.get("created_at"), datetime):
            item["created_at"] = item["created_at"].isoformat()
    return {"items": items, "total": len(items)}


def backfill_single_booking(
    db,
    booking_id: str,
    *,
    dry_run: bool = False,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """Recalcula el precio de UNA reserva sin precio (path canónico).

    Returns:
    - ``None`` → la reserva no existe.
    - ``{"already_priced": True, ...}`` → ya tiene precio; no-op.
    - ``{"skipped": "unpricable", ...}`` → sin tarifa calculable; no escribe.
    - resultado completo → backfilled (escribe a menos que ``dry_run``).

    Mirror exacto del bloque por-reserva de
    ``scripts/migrate_backfill_booking_prices.py``; el script delega aquí
    para tener UNA sola implementación del cálculo + folio + penalizaciones.
    """
    now = now or datetime.now(timezone.utc)
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {
            "_id": 0,
            "booking_id": 1, "prop_id": 1, "status": 1,
            "room_type_id": 1, "rate_plan_id": 1,
            "check_in_date": 1, "check_out_date": 1,
            "rooms": 1, "adults": 1, "children": 1,
            "total_nights": 1, "currency": 1,
            "total_price": 1, "original_total_price": 1,
            "discount_percent": 1, "is_test": 1,
            "stay_status": 1,
            "no_show_penalty_percent": 1, "cancellation_penalty_percent": 1,
            "cancellation_free": 1,
        },
    )
    if booking is None:
        return None

    if booking.get("total_price") is not None:
        return {
            "booking_id": booking_id,
            "already_priced": True,
            "total_price": booking.get("total_price"),
            "status": booking.get("status", ""),
            "prop_id": int(booking.get("prop_id", 0) or 0),
        }

    discount_percent = int(booking.get("discount_percent") or 0)
    total, currency, nights, tax_rate, tax_amount, tax_included = _calculate_total_price(
        prop_id=int(booking.get("prop_id", 0) or 0),
        room_type_id=str(booking.get("room_type_id", "") or ""),
        check_in_date=str(booking.get("check_in_date", "") or ""),
        check_out_date=str(booking.get("check_out_date", "") or ""),
        rooms=int(booking.get("rooms", 1) or 1),
        adults=int(booking.get("adults", 2) or 2),
        children=int(booking.get("children", 0) or 0),
        discount_percent=discount_percent if discount_percent > 0 else None,
        rate_plan_id=booking.get("rate_plan_id") or None,
    )

    if total is None or total <= 0:
        return {
            "booking_id": booking_id,
            "skipped": "unpricable",
            "total_price": None,
            "status": booking.get("status", ""),
            "prop_id": int(booking.get("prop_id", 0) or 0),
        }

    # ``nights`` puede venir None/0 de ``_calculate_total_price`` en casos
    # límite; el fallback al ``total_nights`` del booking mantiene el
    # cálculo consistente (mismo patrón que en la migración).
    effective_nights = int(nights or booking.get("total_nights", 0) or 0)
    penalty_updates = _recompute_penalties(booking, total, nights)
    folio_updates = _recompute_folio(db, booking_id, total, effective_nights, now)
    invoice_updates = _recompute_invoice(db, booking_id, total, now)

    original_total_price = (
        round(total / (1 - discount_percent / 100), 2)
        if discount_percent > 0 and total
        else None
    )
    result: dict[str, Any] = {
        "booking_id": booking_id,
        "status": booking.get("status", ""),
        "prop_id": int(booking.get("prop_id", 0) or 0),
        "total_price": total,
        "currency": currency or booking.get("currency", "USD"),
        "nights": effective_nights,
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "tax_included": tax_included,
        "original_total_price": original_total_price,
        "penalty_recomputed": bool(penalty_updates),
        "folio_recomputed": bool(folio_updates),
        "invoice_recomputed": bool(invoice_updates),
        "already_priced": False,
        "skipped": None,
    }

    if dry_run:
        return result

    update_set: dict[str, Any] = {
        "total_price": total,
        "currency": currency or booking.get("currency", "USD"),
        "total_nights": effective_nights,
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "tax_included": tax_included,
        "original_total_price": original_total_price,
        "pricing_backfilled_at": now,
        "pricing_backfilled_from": MIGRATION_ID,
        "metadata.migration_id": MIGRATION_ID,
    }
    update_set.update(penalty_updates)
    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {"$set": update_set},
    )
    # La factura de la reserva se creó con total 0 (precio None) → corregir
    # subtotal/taxes/total con el precio nuevo, manteniendo el mirror
    # fact_reservation_invoices (update_with_outbox = _update_both).
    if invoice_updates:
        from src.app.modules.billing.service.lifecycle._helpers import (
            FACT_INVOICES,
            INVOICES,
            _update_both,
        )

        _update_both(
            INVOICES,
            FACT_INVOICES,
            invoice_updates["_invoice_id"],
            {"$set": invoice_updates["_update_set"]},
        )

    # El folio de la reserva se creó en check-in con total_price None →
    # posting de habitación en $0. Corregir con el precio nuevo (solo si hay
    # updates — folios sin posting de habitación no se tocan). El filtro
    # incluye ``postings.amount: 0`` para que el write sea atómico con el
    # guard del helper.
    if folio_updates:
        db.guest_folios.update_one(
            {
                "booking_id": booking_id,
                "postings.type": "room",
                "postings.reference_type": "booking",
                "postings.amount": 0,
            },
            {"$set": folio_updates},
        )
    return result


def _recompute_invoice(
    db,
    booking_id: str,
    total: float,
    now: datetime,
) -> dict[str, Any] | None:
    """Recalcular la factura de la reserva que quedó en $0 (mirror de
    ``generate_invoice_for_booking``).

    La factura de una reserva sin precio se creó (o quedó) con
    ``total=0``/``subtotal=0``/``taxes=0``. Con el precio backfilleado se
    recalcula con la misma fórmula canónica:

    - ``room_subtotal = round(total / 1.16, 2)``
    - ``taxes = round(total - room_subtotal, 2)``
    - ``extras_total`` = suma de los ``line_items`` existentes (se preservan)
    - ``subtotal = room_subtotal + extras_total``
    - ``total = subtotal + taxes``

    Solo toca facturas cuyo ``total`` es exactamente 0/ausente (la señal del
    estado roto). Facturas con total real (> 0) no se tocan — podrían tener
    cargos manuales o pagos que no deben recalcularse retroactivamente.

    NOTA de semántica: las facturas rotas de la demo están en estado
    ``cancelled``/``refunded``. El backfill rellena sus montos pero NO cambia
    el estado — es intencional (el huésped ya recibió una factura en $0 que
    debe mostrar el total real). Si un lector futuro ve esto como raro,
    es la decisión documentada de la tarea "recalcular facturas de reservas
    backfilleadas".

    El mirror ``fact_reservation_invoices`` se actualiza en paralelo vía
    ``update_with_outbox`` (el mismo path que ``_update_both`` usa para
    todas las mutaciones de facturas). NOTA: el mirror debe existir (como en
    producción, donde ``_write_both`` los crea con el mismo _id) — el update
    no hace upsert, igual que el resto del código de facturas.

    Devuelve ``{"_update_set": ..., "_invoice_id": ...}`` (o ``None`` si no
    aplica); el llamador decide si lo escribe (via ``update_with_outbox``) o
    solo lo cuenta en ``--dry-run``.
    """
    from src.app.modules.billing.service.lifecycle._helpers import INVOICES

    invoice = db[INVOICES].find_one({"booking_id": booking_id})
    if not invoice:
        return None
    current_total = invoice.get("total")
    if current_total is not None and float(current_total) > 0:
        # Ya tiene cargo real — no es el estado roto que este backfill corrige.
        return None

    room_subtotal = round(total / 1.16, 2)
    taxes = round(total - room_subtotal, 2)
    line_items = invoice.get("line_items") or []
    extras_total = round(
        sum(float(item.get("total", 0) or 0) for item in line_items),
        2,
    )
    subtotal = round(room_subtotal + extras_total, 2)
    invoice_total = round(subtotal + taxes, 2)

    return {
        "_invoice_id": invoice["_id"],
        "_update_set": {
            "room_subtotal": room_subtotal,
            "extras_total": extras_total,
            "subtotal": subtotal,
            "taxes": taxes,
            "total": invoice_total,
            "invoice_backfilled_at": now,
            "invoice_backfilled_from": MIGRATION_ID,
            "metadata.migration_id": MIGRATION_ID,
        },
    }


def recompute_pending_invoices(
    db,
    *,
    exclude_booking_ids: set[str] | None = None,
    dry_run: bool = False,
    now: datetime | None = None,
) -> int:
    """Barrido de facturas rotas de reservas YA con precio.

    El barrido principal de ``backfill_booking_prices`` recalcula la factura
    solo de las reservas que backfillea en la MISMA corrida. Las facturas que
    quedaron en $0 de reservas ya backfilleadas en una corrida anterior (p.
    ej. la demo: ``INV-202607-0005/0006``) necesitan un barrido propio:
    facturas con total 0/ausente cuya reserva tiene ``total_price > 0``.

    ``exclude_booking_ids`` evita el doble conteo en ``--dry-run``: los
    booking_ids ya procesados por el barrido principal se excluyen (en write
    su factura ya no está en $0; en dry-run su factura ya se contó).

    Devuelve cuántas facturas se recalcularon (o se recalcularían en
    ``--dry-run``).
    """
    from src.app.modules.billing.service.lifecycle._helpers import (
        FACT_INVOICES,
        INVOICES,
        _update_both,
    )

    now = now or datetime.now(timezone.utc)
    exclude = exclude_booking_ids or set()
    pending = list(
        db[INVOICES].find(
            {"$or": [{"total": {"$exists": False}}, {"total": None}, {"total": 0}]},
            {"_id": 1, "booking_id": 1},
        )
    )
    recomputed = 0
    for invoice in pending:
        booking_id = invoice.get("booking_id") or ""
        if booking_id in exclude:
            continue
        booking = db.booking_orders.find_one(
            {"booking_id": booking_id}, {"_id": 0, "total_price": 1}
        )
        total = booking.get("total_price") if booking else None
        if total is None or float(total) <= 0:
            continue
        updates = _recompute_invoice(db, booking_id, float(total), now)
        if not updates:
            continue
        if not dry_run:
            _update_both(
                INVOICES,
                FACT_INVOICES,
                updates["_invoice_id"],
                {"$set": updates["_update_set"]},
            )
        recomputed += 1
    return recomputed


def _recompute_folio(
    db,
    booking_id: str,
    total: float,
    nights: int,
    now: datetime,
) -> dict[str, Any] | None:
    """Folio update para una reserva backfilleada (mirror de ``folio.create_folio``).

    El folio se creó en el check-in con ``total_price=None`` → el posting
    inicial de habitación (``type="room"``, ``reference_type="booking"``)
    quedó con ``amount=0`` y ``total_room=0``. Con el precio nuevo:

    - posting de habitación: ``amount = total``, ``unit_price = total/noches``,
      ``quantity = noches`` (misma fórmula que ``create_folio``);
    - ``total_room = total``;
    - ``total_due = total_room + total_charges − total_discounts
      − total_payments`` (con floor en 0, mirror de ``post_to_folio``).

    Solo toca folios cuyo posting de habitación quedó exactamente en $0 (la
    señal del estado roto). Folios de penalización de no-show (sin posting
    de habitación) y folios con cargo real no se tocan.

    Devuelve el ``$set`` (o ``None`` si no aplica); el llamador decide si lo
    escribe o solo lo cuenta en ``--dry-run``.
    """
    safe_nights = int(nights or 0)
    if safe_nights <= 0:
        return None

    folio = db.guest_folios.find_one({"booking_id": booking_id})
    if not folio:
        return None
    room_posting = next(
        (
            p
            for p in (folio.get("postings") or [])
            if p.get("type") == "room" and p.get("reference_type") == "booking"
        ),
        None,
    )
    if room_posting is None or float(room_posting.get("amount", 0) or 0) != 0:
        # Sin posting de habitación (folio de penalización) o ya tiene cargo
        # real: no es el estado roto que este backfill corrige.
        return None

    unit_price = round(total / safe_nights, 2)
    total_due = round(
        total
        + float(folio.get("total_charges", 0) or 0)
        - float(folio.get("total_discounts", 0) or 0)
        - float(folio.get("total_payments", 0) or 0),
        2,
    )
    if total_due < 0:
        total_due = 0.0
    return {
        "total_room": total,
        "total_due": total_due,
        "postings.$.amount": total,
        "postings.$.unit_price": unit_price,
        "postings.$.quantity": safe_nights,
        "folio_backfilled_at": now,
        "folio_backfilled_from": MIGRATION_ID,
        "metadata.migration_id": MIGRATION_ID,
    }


def _recompute_penalties(booking: dict[str, Any], total: float, nights: int) -> dict[str, Any]:
    """Recalcular penalizaciones ya cobradas que quedaron en $0 por falta de precio.

    Replica exactamente las fórmulas canónicas:

    - No-show (``no_show.process_no_show``): rate_per_night = total/noches;
      penalty = rate_per_night × no_show_penalty_percent / 100; si el % es > 0
      y el redondeo da 0, se cobra la noche completa.
    - Cancelación (``cleanup._calculate_cancellation_penalty``): solo si el
      flujo ya decidió cobrar (``cancellation_free`` es False) se recalcula
      one_night × cancellation_penalty_percent / 100 con el % guardado.
      Cancelaciones libres (fuera de ventana) quedan intactas en $0.

    Nunca inventa penalizaciones: si la reserva no está en no-show o el
    flujo no guardó %/decisión de cobro, no toca nada.
    """
    result: dict[str, Any] = {}
    safe_nights = int(nights or booking.get("total_nights", 0) or 0)
    if safe_nights <= 0:
        return result

    # ── No-show ──
    if booking.get("stay_status") == "no_show":
        # ``process_no_show`` SIEMPRE guarda ``no_show_penalty_percent``, así
        # que un 0 guardado es la política real del hotel (0% = sin cargo) y
        # NO debe re-resolverse (resolve_penalty_percent default 100
        # re-cobraría una noche completa retroactivamente). Solo se resuelve
        # cuando el campo está AUSENTE (no-shows legacy pre-campo).
        if booking.get("no_show_penalty_percent") is None:
            pct = resolve_penalty_percent(
                prop_id=int(booking.get("prop_id", 0) or 0),
                room_type_id=str(booking.get("room_type_id", "") or ""),
                rate_plan_id=str(booking.get("rate_plan_id", "") or ""),
            )
        else:
            pct = int(booking.get("no_show_penalty_percent") or 0)
        rate_per_night = round(total / safe_nights, 2)
        penalty = round(rate_per_night * pct / 100, 2)
        if pct > 0 and penalty <= 0:  # mirror de no_show.py:75-76
            penalty = rate_per_night
        result["no_show_penalty_amount"] = penalty
        result["no_show_penalty_percent"] = pct

    # ── Cancelación (solo si el flujo decidió cobrar) ──
    if booking.get("status") == "cancelled" and booking.get("cancellation_free") is False:
        pct = int(booking.get("cancellation_penalty_percent") or 0)
        if pct > 0:
            one_night = round(total / safe_nights, 2)
            penalty = round(one_night * pct / 100, 2)
            result["cancellation_penalty_amount"] = penalty

    return result
