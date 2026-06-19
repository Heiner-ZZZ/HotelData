from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from pymongo import ASCENDING, DESCENDING

from src.database.connection import get_database
from src.app.modules.hotels.service import hotel_detail
from src.app.modules.partner.services import partner_hotel_detail, partner_hotel_policies
from src.app.modules.reservations.schemas import ModuleStatus


ALLOWED_STATUSES = {"requested", "confirmed", "cancelled", "rejected"}
CHECKIN_COMPLETED_STATUSES = {"checked_in", "checked_out"}
CHECKOUT_COMPLETED_STATUSES = {"checked_out"}


@dataclass
class ReservationInput:
    prop_id: int
    guest_name: str
    guest_email: str
    check_in_date: str
    check_out_date: str
    adults: int
    children: int
    rooms: int
    comment: str
    source: str = "web_request"
    user_id: str | None = None
    created_by: str | None = None
    is_test: bool = False


def module_status() -> ModuleStatus:
    return ModuleStatus(
        module="reservations",
        status="partial",
        description="Core minimo de solicitudes de reserva con detalle, cancelacion e ingreso manual sin pagos reales.",
    )


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_now() -> str:
    return utc_now().isoformat()


def generate_prefixed_id(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    token = secrets.token_hex(4)
    return f"{prefix}-{stamp}-{token}".upper()


def ensure_reservation_collections() -> dict[str, Any]:
    db = get_database()
    db.booking_orders.create_index("booking_id", unique=True)
    db.booking_orders.create_index("user_id")
    db.booking_orders.create_index("prop_id")
    db.booking_orders.create_index("status")
    db.booking_orders.create_index([("created_at", DESCENDING)])
    db.booking_guests.create_index("booking_id")
    db.booking_status_history.create_index("booking_id")
    db.booking_status_history.create_index([("changed_at", DESCENDING)])
    db.manual_reservations.create_index("manual_reservation_id", unique=True)
    db.manual_reservations.create_index("booking_id")
    db.manual_reservations.create_index("prop_id")
    db.manual_reservations.create_index([("created_at", DESCENDING)])
    return {
        "collections": [
            "booking_orders",
            "booking_guests",
            "booking_status_history",
            "manual_reservations",
        ],
    }


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def validate_reservation_input(payload: ReservationInput) -> list[str]:
    errors: list[str] = []
    if payload.prop_id <= 0:
        errors.append("prop_id must be a positive integer")
    if not payload.guest_name:
        errors.append("guest_name is required")
    if not payload.guest_email or "@" not in payload.guest_email:
        errors.append("guest_email must be valid")
    if not payload.check_in_date:
        errors.append("check_in_date is required")
    if not payload.check_out_date:
        errors.append("check_out_date is required")
    if payload.adults <= 0:
        errors.append("adults must be greater than zero")
    if payload.children < 0:
        errors.append("children cannot be negative")
    if payload.rooms <= 0:
        errors.append("rooms must be greater than zero")
    if payload.check_in_date and payload.check_out_date and payload.check_out_date < payload.check_in_date:
        errors.append("check_out_date must be greater than or equal to check_in_date")
    return errors


def build_reservation_input(form_data: dict[str, Any], *, source: str, is_test: bool = False) -> ReservationInput:
    return ReservationInput(
        prop_id=_safe_int(form_data.get("prop_id")),
        guest_name=_clean_text(form_data.get("guest_name")),
        guest_email=_clean_text(form_data.get("guest_email")).lower(),
        check_in_date=_clean_text(form_data.get("check_in_date")),
        check_out_date=_clean_text(form_data.get("check_out_date")),
        adults=_safe_int(form_data.get("adults"), 1),
        children=_safe_int(form_data.get("children"), 0),
        rooms=_safe_int(form_data.get("rooms"), 1),
        comment=_clean_text(form_data.get("comment")),
        source=source,
        user_id=_clean_text(form_data.get("user_id")) or None,
        created_by=_clean_text(form_data.get("created_by")) or None,
        is_test=is_test,
    )


def hotel_booking_context(prop_id: int) -> dict[str, Any]:
    detail = hotel_detail(prop_id)
    if detail:
        return {
            "prop_id": prop_id,
            "hotel_label": detail.get("hotel_label") or f"Hotel {prop_id}",
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


def reservation_hotel_options(limit: int = 30) -> list[dict[str, Any]]:
    db = get_database()
    hotels = list(
        db.dim_hotels.find(
            {},
            {
                "_id": 0,
                "prop_id": 1,
                "display_name": 1,
                "display_label": 1,
                "hotel_name": 1,
                "prop_starrating": 1,
            },
        )
        .sort([("display_name", ASCENDING), ("prop_id", ASCENDING)])
        .limit(limit)
    )
    options: list[dict[str, Any]] = []
    for hotel in hotels:
        prop_id = hotel.get("prop_id")
        if prop_id is None:
            continue
        label = (
            hotel.get("display_label")
            or hotel.get("display_name")
            or hotel.get("hotel_name")
            or f"Hotel {prop_id}"
        )
        options.append({"prop_id": prop_id, "label": label})
    return options


def create_booking(payload: ReservationInput, *, manual_reservation: bool = False) -> dict[str, Any]:
    ensure_reservation_collections()
    errors = validate_reservation_input(payload)
    if errors:
        raise ValueError("; ".join(errors))

    db = get_database()
    booking_id = generate_prefixed_id("BK")
    created_at = utc_now()
    booking_document = {
        "booking_id": booking_id,
        "user_id": payload.user_id,
        "prop_id": payload.prop_id,
        "status": "requested",
        "booking_source": payload.source,
        "guest_name": payload.guest_name,
        "guest_email": payload.guest_email,
        "check_in_date": payload.check_in_date,
        "check_out_date": payload.check_out_date,
        "adults": payload.adults,
        "children": payload.children,
        "rooms": payload.rooms,
        "comment": payload.comment,
        "created_by": payload.created_by,
        "created_at": created_at,
        "updated_at": created_at,
        "is_test": payload.is_test,
    }
    db.booking_orders.insert_one(booking_document)
    db.booking_guests.insert_one(
        {
            "booking_id": booking_id,
            "guest_name": payload.guest_name,
            "guest_email": payload.guest_email,
            "is_primary": True,
            "created_at": created_at,
            "is_test": payload.is_test,
        }
    )
    db.booking_status_history.insert_one(
        {
            "booking_id": booking_id,
            "status": "requested",
            "changed_at": created_at,
            "reason": "initial_request",
            "changed_by": payload.created_by or payload.source,
            "is_test": payload.is_test,
        }
    )

    manual_document = None
    if manual_reservation:
        manual_reservation_id = generate_prefixed_id("MR")
        manual_document = {
            "manual_reservation_id": manual_reservation_id,
            "booking_id": booking_id,
            "prop_id": payload.prop_id,
            "created_at": created_at,
            "created_by": payload.created_by or "partner_manual",
            "note": payload.comment,
            "status": "requested",
            "is_test": payload.is_test,
        }
        db.manual_reservations.insert_one(manual_document)

    return {
        "booking_id": booking_id,
        "status": "requested",
        "manual_reservation_id": manual_document["manual_reservation_id"] if manual_document else None,
    }


def list_bookings(page: int = 1, page_size: int = 20) -> dict[str, Any]:
    db = get_database()
    page = max(page, 1)
    page_size = min(max(page_size, 1), 20)
    total = db.booking_orders.count_documents({})
    total_pages = (total + page_size - 1) // page_size if total else 0
    if total_pages and page > total_pages:
        page = total_pages
    items = list(
        db.booking_orders.find({}, {"_id": 0})
        .sort([("created_at", DESCENDING)])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    contexts = {item["booking_id"]: hotel_booking_context(int(item["prop_id"])) for item in items if item.get("prop_id") is not None}
    for item in items:
        item["hotel"] = contexts.get(item["booking_id"])
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_prev": page > 1 and total_pages > 0,
        "has_next": total_pages > 0 and page < total_pages,
    }


def get_booking_detail(booking_id: str) -> dict[str, Any] | None:
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id}, {"_id": 0})
    if booking is None:
        return None
    guest = db.booking_guests.find_one({"booking_id": booking_id, "is_primary": True}, {"_id": 0})
    history = list(db.booking_status_history.find({"booking_id": booking_id}, {"_id": 0}).sort([("changed_at", ASCENDING)]))
    manual = db.manual_reservations.find_one({"booking_id": booking_id}, {"_id": 0})
    return {
        "booking": booking,
        "guest": guest,
        "history": history,
        "manual": manual,
        "hotel": hotel_booking_context(int(booking["prop_id"])) if booking.get("prop_id") is not None else None,
        "can_cancel": booking.get("status") == "requested",
    }


def cancel_booking(booking_id: str, *, reason: str = "cancelled_by_user", changed_by: str = "web") -> dict[str, Any]:
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id})
    if booking is None:
        raise ValueError("booking not found")
    if booking.get("status") != "requested":
        raise ValueError("only requested bookings can be cancelled")
    changed_at = utc_now()
    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {"$set": {"status": "cancelled", "updated_at": changed_at, "cancel_reason": reason}},
    )
    db.booking_status_history.insert_one(
        {
            "booking_id": booking_id,
            "status": "cancelled",
            "changed_at": changed_at,
            "reason": reason,
            "changed_by": changed_by,
            "is_test": bool(booking.get("is_test")),
        }
    )
    if db.manual_reservations.count_documents({"booking_id": booking_id}) > 0:
        db.manual_reservations.update_one(
            {"booking_id": booking_id},
            {"$set": {"status": "cancelled", "updated_at": changed_at}},
        )
    return {"booking_id": booking_id, "status": "cancelled"}


def cleanup_test_booking(booking_id: str) -> dict[str, Any]:
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id}, {"_id": 0, "is_test": 1})
    if booking is None:
        return {"booking_id": booking_id, "deleted": False, "reason": "not_found"}
    if not booking.get("is_test"):
        return {"booking_id": booking_id, "deleted": False, "reason": "not_marked_as_test"}
    deleted = {
        "booking_orders": db.booking_orders.delete_one({"booking_id": booking_id}).deleted_count,
        "booking_guests": db.booking_guests.delete_many({"booking_id": booking_id}).deleted_count,
        "booking_status_history": db.booking_status_history.delete_many({"booking_id": booking_id}).deleted_count,
        "manual_reservations": db.manual_reservations.delete_many({"booking_id": booking_id}).deleted_count,
    }
    return {"booking_id": booking_id, "deleted": True, "counts": deleted}


def _booking_history_lookup(booking_ids: list[str]) -> dict[str, list[dict[str, Any]]]:
    if not booking_ids:
        return {}
    db = get_database()
    items = list(
        db.booking_status_history.find({"booking_id": {"$in": booking_ids}}, {"_id": 0})
        .sort([("changed_at", ASCENDING)])
    )
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        grouped.setdefault(item["booking_id"], []).append(item)
    return grouped


def _guest_lookup(booking_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not booking_ids:
        return {}
    db = get_database()
    guests = list(
        db.booking_guests.find(
            {"booking_id": {"$in": booking_ids}, "is_primary": True},
            {"_id": 0},
        )
    )
    return {item["booking_id"]: item for item in guests}


def _derived_stay_status(booking: dict[str, Any], history: list[dict[str, Any]], *, flow: str) -> str:
    explicit = str(booking.get("stay_status") or "").strip().lower()
    if explicit:
        return explicit
    statuses = [str(item.get("status") or "").strip().lower() for item in history]
    if "checked_out" in statuses:
        return "checked_out"
    if "checked_in" in statuses:
        return "checked_in"
    if booking.get("status") == "cancelled":
        return "cancelled"
    if booking.get("status") == "rejected":
        return "no_show" if flow == "check_in" else "cancelled"
    return "pending"


def _reservation_status_label(status: str) -> str:
    mapping = {
        "requested": "Pendiente",
        "confirmed": "Confirmada",
        "cancelled": "Cancelada",
        "rejected": "Rechazada",
        "checked_in": "Check-in completado",
        "checked_out": "Check-out completado",
        "pending": "Pendiente",
        "no_show": "No-show",
    }
    return mapping.get(status, status or "Pendiente")


def _operational_item(
    booking: dict[str, Any],
    guest: dict[str, Any] | None,
    history: list[dict[str, Any]],
    *,
    flow: str,
) -> dict[str, Any]:
    hotel = hotel_booking_context(int(booking["prop_id"]))
    policies = partner_hotel_policies(int(booking["prop_id"])) or {}
    policy_data = policies.get("policies", {})
    stay_status = _derived_stay_status(booking, history, flow=flow)
    reference_time = (
        policy_data.get("check_in_time")
        if flow == "check_in"
        else policy_data.get("check_out_time")
    ) or "N/D"
    rooms = _safe_int(booking.get("rooms"), 1)
    room_label = f"{rooms} habitacion(es)" if rooms > 0 else "Sin asignar"
    comment = _clean_text(booking.get("comment"))
    return {
        "booking_id": booking["booking_id"],
        "prop_id": int(booking["prop_id"]),
        "hotel_label": hotel.get("hotel_label") or f"Hotel {booking['prop_id']}",
        "guest_name": (guest or {}).get("guest_name") or booking.get("guest_name") or "Huesped principal",
        "guest_email": (guest or {}).get("guest_email") or booking.get("guest_email") or "",
        "date": booking.get("check_in_date") if flow == "check_in" else booking.get("check_out_date"),
        "reservation_status": str(booking.get("status") or "requested"),
        "reservation_status_label": _reservation_status_label(str(booking.get("status") or "requested")),
        "stay_status": stay_status,
        "stay_status_label": _reservation_status_label(stay_status),
        "rooms_label": room_label,
        "estimated_time": reference_time,
        "notes": comment or "Sin notas",
        "balance_label": "N/D",
        "can_complete": stay_status not in (CHECKIN_COMPLETED_STATUSES if flow == "check_in" else CHECKOUT_COMPLETED_STATUSES)
        and booking.get("status") not in {"cancelled", "rejected"},
        "history_count": len(history),
    }


def _list_operational_bookings(*, flow: str, operation_date: str, prop_id: int | None = None) -> dict[str, Any]:
    db = get_database()
    field = "check_in_date" if flow == "check_in" else "check_out_date"
    filters: dict[str, Any] = {field: operation_date}
    if prop_id:
        filters["prop_id"] = prop_id
    items = list(
        db.booking_orders.find(filters, {"_id": 0}).sort([(field, ASCENDING), ("created_at", ASCENDING)])
    )
    booking_ids = [item["booking_id"] for item in items]
    guest_lookup = _guest_lookup(booking_ids)
    history_lookup = _booking_history_lookup(booking_ids)
    view_items = [
        _operational_item(item, guest_lookup.get(item["booking_id"]), history_lookup.get(item["booking_id"], []), flow=flow)
        for item in items
    ]
    total = len(view_items)
    completed_key = "checked_in" if flow == "check_in" else "checked_out"
    summary = {
        "arrivals_today" if flow == "check_in" else "departures_today": total,
        "pending": sum(1 for item in view_items if item["stay_status"] == "pending"),
        "completed": sum(1 for item in view_items if item["stay_status"] == completed_key),
        "cancelled_or_no_show": sum(1 for item in view_items if item["stay_status"] in {"cancelled", "no_show"}),
    }
    return {
        "operation_date": operation_date,
        "prop_id": prop_id,
        "property_options": reservation_hotel_options(limit=100),
        "summary": summary,
        "items": view_items,
    }


def list_check_ins(*, operation_date: str, prop_id: int | None = None) -> dict[str, Any]:
    return _list_operational_bookings(flow="check_in", operation_date=operation_date, prop_id=prop_id)


def list_check_outs(*, operation_date: str, prop_id: int | None = None) -> dict[str, Any]:
    return _list_operational_bookings(flow="check_out", operation_date=operation_date, prop_id=prop_id)


def complete_check_in(booking_id: str, *, changed_by: str = "angular_api") -> dict[str, Any]:
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id}, {"_id": 0})
    if booking is None:
        raise ValueError("booking not found")
    history = _booking_history_lookup([booking_id]).get(booking_id, [])
    stay_status = _derived_stay_status(booking, history, flow="check_in")
    if stay_status in CHECKIN_COMPLETED_STATUSES:
        raise ValueError("booking already checked in")
    if booking.get("status") in {"cancelled", "rejected"}:
        raise ValueError("booking cannot be checked in from current reservation status")
    changed_at = utc_now()
    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {"$set": {"stay_status": "checked_in", "updated_at": changed_at}},
    )
    db.booking_status_history.insert_one(
        {
            "booking_id": booking_id,
            "status": "checked_in",
            "changed_at": changed_at,
            "reason": "front_desk_check_in",
            "changed_by": changed_by,
            "is_test": bool(booking.get("is_test")),
        }
    )
    return {"booking_id": booking_id, "stay_status": "checked_in"}


def complete_check_out(booking_id: str, *, changed_by: str = "angular_api") -> dict[str, Any]:
    db = get_database()
    booking = db.booking_orders.find_one({"booking_id": booking_id}, {"_id": 0})
    if booking is None:
        raise ValueError("booking not found")
    history = _booking_history_lookup([booking_id]).get(booking_id, [])
    stay_status = _derived_stay_status(booking, history, flow="check_out")
    if stay_status in CHECKOUT_COMPLETED_STATUSES:
        raise ValueError("booking already checked out")
    if booking.get("status") in {"cancelled", "rejected"}:
        raise ValueError("booking cannot be checked out from current reservation status")
    changed_at = utc_now()
    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {"$set": {"stay_status": "checked_out", "updated_at": changed_at}},
    )
    db.booking_status_history.insert_one(
        {
            "booking_id": booking_id,
            "status": "checked_out",
            "changed_at": changed_at,
            "reason": "front_desk_check_out",
            "changed_by": changed_by,
            "is_test": bool(booking.get("is_test")),
        }
    )
    return {"booking_id": booking_id, "stay_status": "checked_out"}
