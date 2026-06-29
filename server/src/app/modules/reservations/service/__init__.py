from __future__ import annotations

from src.app.modules.reservations.schemas import ModuleStatus
from .validation import validate_reservation_input, build_reservation_input
from .collections import ensure_reservation_collections
from .queries import hotel_booking_context, list_bookings, get_booking_detail, list_reservation_dates, get_reservation_stats
from ._hotel_options import reservation_hotel_options
from .lifecycle import create_booking, get_room_guests, save_room_guests, get_check_in_status, modify_booking, validate_coupon_code
from ._transitions import confirm_booking, reject_booking
from .cleanup import auto_cancel_expired_pending, cancel_booking, cleanup_test_booking
from ._view_ops import list_check_ins, list_check_outs, list_check_in_dates, list_check_out_dates
from ._checkinout import complete_check_in, complete_check_out
from ._checkin_detail import get_check_in_detail, save_check_in_detail
from ._checkout_detail import get_check_out_detail, save_check_out_detail


def module_status() -> ModuleStatus:
    return ModuleStatus(
        module="reservations",
        status="partial",
        description="Solicitudes de reserva con disponibilidad, precio, teléfono huésped, historial de estados, check-in/out manual sin pagos reales.",
    )


__all__ = [
    "module_status",
    "ensure_reservation_collections",
    "validate_reservation_input",
    "build_reservation_input",
    "hotel_booking_context",
    "reservation_hotel_options",
    "create_booking",
    "get_room_guests",
    "save_room_guests",
    "get_check_in_status",
    "modify_booking",
    "list_bookings",
    "get_booking_detail",
    "list_reservation_dates",
    "get_reservation_stats",
    "confirm_booking",
    "reject_booking",
    "auto_cancel_expired_pending",
    "cancel_booking",
    "cleanup_test_booking",
    "list_check_ins",
    "list_check_outs",
    "list_check_in_dates",
    "list_check_out_dates",
    "complete_check_in",
    "complete_check_out",
    "get_check_in_detail",
    "save_check_in_detail",
    "get_check_out_detail",
    "save_check_out_detail",
]
