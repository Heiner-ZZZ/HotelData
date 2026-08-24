from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING

from src.app.core.timezone import local_today
from src.app.modules.hotels.service import hotel_detail
from src.app.modules.partner.services import (
    partner_hotel_detail,
    partner_hotel_policies,
)
from src.app.modules.reservations.service.no_show import reopen_window_reason
from src.app.security.hotel_filter import hotel_filter_from_user
from src.app.security.role_helpers import get_role_name
from src.database.connection import get_database

logger = logging.getLogger(__name__)


def _json_safe(obj: Any) -> Any:
    """Recursively convert ObjectIds + datetimes to JSON-safe primitive types.

    Extended from the original (which only handled ObjectId) to also
    isoformat ``datetime`` objects. ``list_bookings`` now wraps its
    return payload with this helper so the raw BSON docs survive
    ``BookingListResponse.model_validate(...)``. See reservation routes
    reservations.py:70 + schemas.py ReservationResponse strict types.
    """
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    return obj


def hotel_booking_context(prop_id: int) -> dict[str, Any]:
    detail = hotel_detail(prop_id)
    if detail:
        # get_hotel_detail_view() returns the enriched view with the hotel doc
        # nested under ``detail["hotel"]`` (display_name/hotel_name live there),
        # NOT at the top level. Reading the top level silently fell back to
        # ``f"Hotel {prop_id}"`` (e.g. "Hotel 1") even when dim_hotels had a
        # real name. Read the nested doc for the label; metrics stay top-level.
        hotel_doc = detail.get("hotel") or {}
        return {
            "prop_id": prop_id,
            "hotel_label": hotel_doc.get("display_name") or hotel_doc.get("hotel_name") or f"Hotel {prop_id}",
            "country": detail.get("prop_country_id"),
            "review_label": detail.get("review_label"),
            "avg_price_label": detail.get("avg_price_label"),
        }
    partner = partner_hotel_detail(prop_id)
    if partner:
        hotel = partner["hotel"]
        return {
            "prop_id": prop_id,
            "hotel_label": hotel.get("display_name") or hotel.get("hotel_name") or f"Hotel {prop_id}",
            "country": hotel.get("prop_country_id"),
            "review_label": hotel.get("review_score_label"),
            "avg_price_label": partner["performance"].get("avg_price_label"),
        }
    return {"prop_id": prop_id, "hotel_label": f"Hotel {prop_id}", "country": None, "review_label": "N/D", "avg_price_label": "N/D"}


def list_bookings(
    page: int = 1,
    page_size: int = 20,
    created_date: str | None = None,
    status: str | None = None,
    prop_id: int | None = None,
    guest_name: str | None = None,
    folio: str | None = None,
    stay_status: str | None = None,
    booking_source: str | None = None,
    user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    db = get_database()
    page = max(page, 1)
    page_size = min(max(page_size, 1), 20)
    filters: dict[str, Any] = {}
    # Apply user/hotel filter
    user_filter = hotel_filter_from_user(user)
    if user_filter:
        filters.update(user_filter)
    # Client role: filter by user_id so they only see their own bookings.
    # ``user_id`` is stored as a BSON ObjectId FK (canonical since the
    # 2026-Q3 migration), so the filter must use the raw ObjectId — a string
    # comparison would silently hide every booking from its owner.
    if user and get_role_name(user) == "cliente":
        uid = user.get("_id")
        if uid:
            # Auth middleware always hands a BSON ObjectId; harden against a
            # legacy hex-string _id so the ObjectId filter still matches.
            if isinstance(uid, str) and ObjectId.is_valid(uid):
                uid = ObjectId(uid)
            filters["user_id"] = uid
    # Optional filters
    if status:
        filters["status"] = status
    if prop_id:
        filters["prop_id"] = prop_id
    if folio:
        filters["folio"] = {"$regex": folio, "$options": "i"}
    if stay_status == "none":
        # "Sin check-in" → show bookings where stay_status is empty/null
        filters["$or"] = [{"stay_status": {"$exists": False}}, {"stay_status": ""}, {"stay_status": None}]
    elif stay_status:
        filters["stay_status"] = stay_status


    if guest_name:
        # Find booking IDs matching guest name (case‑insensitive)
        regex = {"$regex": guest_name, "$options": "i"}
        guest_cursor = db.booking_guests.find({"guest_name": regex}, {"booking_id": 1})
        booking_ids = [doc["booking_id"] for doc in guest_cursor]
        if not booking_ids:
            # No matches → return empty pagination result
            return {
                "items": [],
                "page": page,
                "page_size": page_size,
                "total": 0,
                "total_pages": 0,
                "has_prev": False,
                "has_next": False,
            }
        filters["booking_id"] = {"$in": booking_ids}
    if created_date:
        filters["$expr"] = {"$eq": [{"$substr": ["$created_at", 0, 10]}, created_date]}
    total = db.booking_orders.count_documents(filters)
    total_pages = (total + page_size - 1) // page_size if total else 0
    if total_pages and page > total_pages:
        page = total_pages
    items = list(
        db.booking_orders.find(filters)
        .sort([("created_at", DESCENDING)])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    contexts = {item["booking_id"]: hotel_booking_context(int(item["prop_id"])) for item in items if item.get("prop_id") is not None}
    # Enrich with cedula from booking_guests
    booking_ids = [item["booking_id"] for item in items if item.get("booking_id")]
    cedula_map: dict[str, str] = {}
    if booking_ids:
        for g in db.booking_guests.find(
            {"booking_id": {"$in": booking_ids}, "is_primary": True},
            {"booking_id": 1, "cedula": 1, "_id": 0},
        ):
            if g.get("cedula"):
                cedula_map[g["booking_id"]] = g["cedula"]
    today_str = local_today()
    for item in items:
        item["hotel"] = contexts.get(item["booking_id"])
        item["cedula"] = cedula_map.get(item.get("booking_id", ""), "")
        # Ventana de reapertura de no-show (server-authoritative, misma regla
        # que el calendario de Recepción vía ``reopen_window_reason``): la lista
        # marca los no-shows sin abrir el timeline. También marca las reservas
        # REABIERTAS (``no_show_reopened_at``: el gerente reabrió porque el
        # huésped llegó tras el no-show) con la misma ventana, para que
        # recepción las detecte sin abrir el calendario — mismo criterio que el
        # banner ``reopenedNotice`` del detalle de check-in. Solo estos dos
        # casos llevan ventana; el resto queda en ``None``.
        stay_status_lower = str(item.get("stay_status") or "").strip().lower()
        if stay_status_lower == "no_show" or item.get("no_show_reopened_at"):
            item["reopen_window"] = reopen_window_reason(item, today_str) or "open"
        else:
            item["reopen_window"] = None
        # Serialize ObjectId FK fields for JSON
        if isinstance(item.get("coupon_id"), ObjectId):
            item["coupon_id"] = str(item["coupon_id"])
    return _json_safe({
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_prev": page > 1 and total_pages > 0,
        "has_next": total_pages > 0 and page < total_pages,
    })


def list_past_stays(
    *,
    prop_id: int | None = None,
    limit: int = 12,
    user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Estadías pasadas del huésped, en modo lectura (zona sin acciones).

    Devuelve los bookings TERMINADOS del usuario: check-outs completados,
    no-shows y reservas cuyas fechas ya vencieron. Cada item lleva
    ``read_only_reason`` (server-authoritative) que explica por qué la zona
    no ofrece acciones:

    - ``no_show``      → marcada como No Show (no se presentó en el check-in).
    - ``dates_passed`` → las fechas de la estadía ya pasaron.

    Scope: el ``cliente`` ve SOLO sus reservas (FK ``user_id``); el staff
    conserva su filtro multi-hotel canónico. Canceladas/rechazadas quedan
    fuera: no son estadías.
    """
    db = get_database()
    today_str = local_today()
    filters: dict[str, Any] = {
        "status": {"$nin": ["cancelled", "rejected"]},
        "$or": [
            {"stay_status": {"$in": ["checked_out", "no_show"]}},
            {"check_out_date": {"$lt": today_str}},
        ],
    }
    if prop_id:
        filters["prop_id"] = prop_id
    if user and get_role_name(user) == "cliente":
        uid = user.get("_id")
        if uid:
            # Mismo hardening ObjectId que list_bookings: el FK canónico es
            # BSON; un string heredado no matchearía a su dueño.
            if isinstance(uid, str) and ObjectId.is_valid(uid):
                uid = ObjectId(uid)
            filters["user_id"] = uid
    else:
        user_filter = hotel_filter_from_user(user)
        if user_filter:
            filters.update(user_filter)

    docs = list(
        db.booking_orders.find(filters)
        .sort([("check_out_date", DESCENDING), ("created_at", DESCENDING)])
        .limit(max(1, min(limit, 50)))
    )
    items: list[dict[str, Any]] = []
    for b in docs:
        stay = str(b.get("stay_status") or "").strip().lower()
        reason = "no_show" if stay == "no_show" else "dates_passed"
        context = (
            hotel_booking_context(int(b["prop_id"]))
            if b.get("prop_id") is not None else {}
        )
        items.append({
            "booking_id": b.get("booking_id", ""),
            "prop_id": int(b.get("prop_id") or 0),
            "hotel_label": context.get("hotel_label") or f"Hotel {b.get('prop_id')}",
            "guest_name": b.get("guest_name", ""),
            "check_in_date": str(b.get("check_in_date") or ""),
            "check_out_date": str(b.get("check_out_date") or ""),
            "total_price": float(b["total_price"]) if b.get("total_price") is not None else None,
            "currency": b.get("currency") or "USD",
            "status": str(b.get("status") or ""),
            "stay_status": stay,
            "read_only_reason": reason,
            "no_show_penalty_amount": (
                float(b["no_show_penalty_amount"])
                if b.get("no_show_penalty_amount") is not None else None
            ),
        })
    return {"items": _json_safe(items)}


def list_reservation_dates(*, prop_id: int | None = None, user: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Return distinct created_at dates with booking count, optionally filtered by property."""
    """Return distinct created_at dates with booking count, optionally filtered by property."""
    db = get_database()
    filters: dict[str, Any] = {}
    user_filter = hotel_filter_from_user(user)
    if user_filter:
        filters.update(user_filter)
    if prop_id:
        filters["prop_id"] = prop_id
    # created_at is stored as ISO string, use $substr to extract date part
    pipeline: list[dict[str, Any]] = [
        {"$match": filters},
        {"$group": {
            "_id": {"$substr": ["$created_at", 0, 10]},
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id": -1}},
        {"$project": {"_id": 0, "date": "$_id", "count": 1}},
    ]
    return list(db.booking_orders.aggregate(pipeline))


def get_reservation_stats(user: dict[str, Any] | None = None) -> dict[str, int]:
    """Return counts per status and aggregate fields.

    The test suite expects the keys:
    - pending, confirmed, cancelled, rejected, checked_in, checked_out
    - total, active, completed, lost
    """
    db = get_database()
    # Base match: apply hotel filter if user provided
    base_match = hotel_filter_from_user(user) or {}
    pipeline = [
        {"$match": base_match},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    results = list(db.booking_orders.aggregate(pipeline))
    stats = {r["_id"]: r["count"] for r in results}
    # Ensure all expected statuses exist with 0
    for s in ("pending", "confirmed", "cancelled", "rejected", "checked_in", "checked_out"):
        stats.setdefault(s, 0)
    # Aggregates
    total = sum(stats.values())
    active = stats["pending"] + stats["confirmed"]
    completed = stats["checked_in"] + stats["checked_out"]
    lost = stats["rejected"] + stats["cancelled"]
    stats.update({"total": total, "active": active, "completed": completed, "lost": lost})
    return stats


def _lookup_room_type(db: Any, room_type_id: str, prop_id: int) -> dict | None:
    """Look up room type name from room_type_id."""
    if not room_type_id:
        return None
    rt = db.room_types.find_one({"room_type_id": room_type_id}, {"_id": 0, "name": 1})
    if rt:
        return {"room_type_id": room_type_id, "name": rt.get("name", room_type_id)}
    return {"room_type_id": room_type_id, "name": room_type_id}


def _build_price_breakdown(
    db: Any,
    prop_id: int,
    room_type_id: str,
    check_in_date: str,
    check_out_date: str,
    rooms: int,
    total_price: float | None,
    total_nights: int,
) -> dict | None:
    """Build per-night price breakdown.

    1. Attempts to fetch actual per-night rates from hotel_rate_calendar.
    2. Falls back to deriving from total_price / total_nights.
    Returns None if no pricing data is available.

    Invariante de consistencia (regresión no-show/desglose): el ``total`` del
    desglose SIEMPRE es el precio final de la reserva (el mismo que ve la
    factura y el resumen financiero). El IVA se muestra como split de
    presentación idéntico al de la factura (subtotal = total / 1.16); nunca
    se suma IVA ENCIMA de un total que ya lo incluye. El total a cobrar se
    calcula con la misma lógica de ``_calculate_total_price``: las tarifas
    del calendario son brutas cuando el plan tiene IVA incluido y netas
    cuando no (entonces se suma la tasa del plan).
    """
    if not check_in_date or not check_out_date or not total_nights:
        return None

    try:
        cin = date.fromisoformat(check_in_date)
        cout = date.fromisoformat(check_out_date)
    except (ValueError, TypeError):
        return None

    date_list = [(cin + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((cout - cin).days)]

    # Try to get actual per-night rates from calendar
    rate_query = {"prop_id": prop_id, "date": {"$in": date_list}}
    if room_type_id:
        rate_query["room_type_id"] = room_type_id
    calendar_rates = list(
        db.hotel_rate_calendar.find(rate_query, {"_id": 0, "date": 1, "rate_amount": 1, "rate_plan_id": 1, "tax_included": 1, "tax_rate": 1}).sort("date", 1)
    )

    def _resolve_tax_settings() -> tuple[bool, float]:
        """Mismo lookup que ``_calculate_total_price``: plan + overrides por fecha."""
        tax_included = False
        tax_rate = 0.0
        if calendar_rates:
            rpid = calendar_rates[0].get("rate_plan_id") or ""
            if rpid:
                plan = db.rate_plans.find_one(
                    {"rate_plan_id": rpid},
                    {"_id": 0, "tax_included": 1, "tax_rate": 1},
                )
                if plan:
                    tax_included = bool(plan.get("tax_included", False))
                    tax_rate = float(plan.get("tax_rate") or 0)
            first_record_tax = calendar_rates[0].get("tax_included")
            first_record_tax_rate = calendar_rates[0].get("tax_rate")
            if first_record_tax is not None:
                tax_included = bool(first_record_tax)
            if first_record_tax_rate is not None:
                tax_rate = float(first_record_tax_rate)
        return tax_included, tax_rate

    def _split_total(total: float) -> tuple[float, float]:
        """Split de presentación igual al de la factura: subtotal = total/1.16.

        El IVA mostrado queda embebido en el total final (el huésped paga
        ``total``), nunca se suma encima. 16% fijo de display, igual que
        ``generate_invoice_for_booking``.
        """
        subtotal = round(total / 1.16, 2)
        taxes = round(total - subtotal, 2)
        return subtotal, taxes

    if calendar_rates and len(calendar_rates) == len(date_list):
        # All rates found in calendar
        tax_included, tax_rate = _resolve_tax_settings()
        nights = []
        base = 0.0
        for cr in calendar_rates:
            night_total = float(cr["rate_amount"]) * rooms
            nights.append({"date": cr["date"], "rate": float(cr["rate_amount"]), "rooms": rooms, "night_total": round(night_total, 2)})
            base += night_total
        base = round(base, 2)
        # Total final a cobrar: tarifas brutas si el IVA va incluido; si el
        # plan NO lo incluye y tiene tasa, se suma la tasa del plan.
        if not tax_included and tax_rate > 0:
            total = round(base * (1 + tax_rate / 100), 2)
        else:
            total = base
        subtotal, taxes = _split_total(total)
        return {
            "nights": nights,
            "subtotal": subtotal,
            "taxes": taxes,
            "iva_rate": 0.16,
            "total": total,
            "currency": "USD",
            "source": "calendar",
        }
    elif total_price and total_price > 0:
        # Derive from total_price — que es el precio FINAL. Nunca sumarle IVA
        # encima: eso duplicaba el impuesto y el desglose decía $218.08 cuando
        # la factura decía $188.00 (regresión no-show).
        rate_per_night = round(total_price / total_nights, 2)
        nights = []
        for d in date_list:
            night_total = rate_per_night
            nights.append({"date": d, "rate": rate_per_night, "rooms": rooms, "night_total": round(night_total, 2)})
        total = round(total_price, 2)
        subtotal, taxes = _split_total(total)
        return {
            "nights": nights,
            "subtotal": subtotal,
            "taxes": taxes,
            "iva_rate": 0.16,
            "total": total,
            "currency": "USD",
            "source": "derived",
        }

    return None


def _get_cancellation_policy(db: Any, prop_id: int) -> str | None:
    """Get the hotel-wide cancellation policy text."""
    try:
        policies_data = partner_hotel_policies(prop_id)
        if policies_data:
            policy = policies_data.get("policies", {})
            text = policy.get("cancellation_policy", "")
            return text if text else None
    except Exception:
        logger.exception("Failed to fetch cancellation policy for prop_id %s", prop_id)
    return None


def get_booking_detail(booking_id: str) -> dict[str, Any] | None:

    db = get_database()

    booking_doc = db.booking_orders.find_one({"booking_id": booking_id}, {"_id": 1})
    if booking_doc is None:
        return None
    booking_oid = booking_doc["_id"]

    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if booking is None:
        return None
    guest = db.booking_guests.find_one({"booking_id": booking_id, "is_primary": True}, {"_id": 0})
    history = list(db.booking_status_history.find({"booking_id": booking_id}).sort([("changed_at", ASCENDING)]))
    manual = db.manual_reservations.find_one({"booking_id": booking_id}, {"_id": 0})

    # Invoice
    # ``reservation_invoices.booking_id`` is normally the business key
    # (``BK-...``). A historical migration stored the booking Mongo ``_id``
    # instead, so accept both references when rebuilding the detail after a
    # reload. The booking key remains the canonical value for new writes.
    booking_references: list[Any] = [booking_id]
    if booking_oid is not None:
        booking_references.append(booking_oid)
    invoice = db.reservation_invoices.find_one(
        {"booking_id": {"$in": booking_references}},
        {"_id": 1, "invoice_number": 1, "subtotal": 1, "taxes": 1, "total": 1, "status": 1, "issued_at": 1, "paid_at": 1},
    )
    invoice_data = None
    if invoice:
        invoice_data = {
            "id": str(invoice["_id"]),
            "invoice_number": invoice.get("invoice_number"),
            "subtotal": invoice.get("subtotal"),
            "taxes": invoice.get("taxes"),
            "total": invoice.get("total"),
            "status": invoice.get("status"),
            "issued_at": invoice.get("issued_at").isoformat() if invoice.get("issued_at") else None,
            "paid_at": invoice.get("paid_at").isoformat() if invoice.get("paid_at") else None,
        }

    # Folio de penalización por no-show: fuente de verdad del importe a cobrar
    # cuando el huésped no se presentó (la factura de la estadía queda como
    # referencia, NO como monto pendiente). ``process_no_show`` crea el folio
    # con la penalización de la primera noche; aquí solo se expone el número
    # para que el detalle muestre el importe correcto.
    no_show_folio_number = None
    if booking.get("stay_status") == "no_show":
        _folio = db.guest_folios.find_one({"booking_id": booking_id}, {"folio_number": 1})
        if _folio:
            no_show_folio_number = _folio.get("folio_number")

    # Room type
    room_type = _lookup_room_type(db, booking.get("room_type_id", ""), int(booking.get("prop_id", 0)))

    # Price breakdown
    price_breakdown = _build_price_breakdown(
        db=db,
        prop_id=int(booking.get("prop_id", 0)),
        room_type_id=booking.get("room_type_id", ""),
        check_in_date=booking.get("check_in_date", ""),
        check_out_date=booking.get("check_out_date", ""),
        rooms=int(booking.get("rooms", 1)),
        total_price=booking.get("total_price"),
        total_nights=int(booking.get("total_nights", 0)),
    )

    # Additional charges (amenities, room service, etc.)
    from src.app.modules.housekeeping.service.collections import CHARGES_COLLECTION
    additional_charges = list(
        db[CHARGES_COLLECTION].find({"booking_id": booking_id}, {"_id": 0}).sort([("created_at", -1)])
    )

    # Count how many of those charges are amenities (requested via the guest flow)
    amenities_charges = [c for c in additional_charges if c.get("concept", "").startswith("Amenidad solicitada:")]
    amenities_count = len(amenities_charges)
    amenities_total = round(sum(c.get("total", 0) or 0 for c in amenities_charges), 2)

    # Assigned rooms with their current status from room_status_log
    assigned_rooms: list[dict[str, Any]] = []
    raw_ids: list[str] = booking.get("assigned_rooms") or []
    if raw_ids:
        # Resolve room labels from hotel_rooms
        room_docs = list(
            db.hotel_rooms.find(
                {"hotel_room_id": {"$in": raw_ids}},
                {"_id": 0, "hotel_room_id": 1, "room_label": 1, "floor": 1},
            )
        )
        # Fetch status for each room
        labels = [r.get("room_label", "") for r in room_docs if r.get("room_label")]
        status_map: dict[str, str] = {}
        if labels:
            for doc in db.room_status_log.find(
                {"prop_id": int(booking.get("prop_id", 0)), "room_label": {"$in": labels}},
                {"_id": 0, "room_label": 1, "status": 1},
            ):
                status_map[doc["room_label"]] = doc["status"]

        for r in room_docs:
            label = r.get("room_label", "")
            assigned_rooms.append({
                "hotel_room_id": r["hotel_room_id"],
                "room_number": r.get("room_label", ""),
                "room_label": r.get("room_label", ""),
                "floor": r.get("floor", ""),
                "room_status": status_map.get(label, "unknown"),
            })

    # Cancellation policy
    cancellation_policy = _get_cancellation_policy(db, int(booking.get("prop_id", 0)))

    # Depósito real (política de pago por adelantado): el pago registrado al
    # confirmar la reserva vía billing (``payment_source="deposit"``). Nunca
    # se deriva de metadata de tarjeta — el stub que marcaba "paid" en falso
    # fue eliminado (2026-08).
    deposit = db.reservation_payments.find_one(
        {"booking_id": booking_id, "payment_source": "deposit"},
        {"_id": 0, "amount": 1, "method": 1, "reference": 1, "status": 1, "paid_at": 1},
        sort=[("paid_at", -1)],
    )
    deposit_data = None
    if deposit:
        deposit_data = {
            "amount": round(float(deposit.get("amount", 0) or 0), 2),
            "method": deposit.get("method"),
            "reference": deposit.get("reference"),
            "status": deposit.get("status"),
            "paid_at": deposit.get("paid_at").isoformat() if deposit.get("paid_at") else None,
        }

    from src.app.modules.reservations.service.special_request_fulfillment import (
        get_amenity_fulfillment,
        get_special_request_fulfillment,
    )

    return _json_safe({
        "booking": booking,
        "deposit": deposit_data,
        "special_request_fulfillment": get_special_request_fulfillment(booking),
        "amenity_fulfillment": get_amenity_fulfillment(booking),
        "guest": guest,
        "history": history,
        "manual": manual,
        "hotel": hotel_booking_context(int(booking["prop_id"])) if booking.get("prop_id") is not None else None,
        "invoice": invoice_data,
        "no_show_folio_number": no_show_folio_number,
        "room_type": room_type,
        "price_breakdown": price_breakdown,
        "cancellation_policy": cancellation_policy,
        "additional_charges": additional_charges,
        "assigned_rooms": assigned_rooms,
        "amenities_count": amenities_count,
        "amenities_total": amenities_total,
        "can_cancel": booking.get("status") in {"pending", "confirmed"},
    })
