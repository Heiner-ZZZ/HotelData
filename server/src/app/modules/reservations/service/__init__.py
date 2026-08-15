from __future__ import annotations

from src.app.modules.reservations.schemas import ModuleStatus

from ._checkin_detail import get_check_in_detail, save_check_in_detail
from ._checkinout import complete_check_in, complete_check_out
from ._checkout_detail import get_check_out_detail, save_check_out_detail
from ._hotel_options import reservation_hotel_options
from ._transitions import confirm_booking, reject_booking
from ._view_ops import (
    list_check_in_dates,
    list_check_ins,
    list_check_out_dates,
    list_check_outs,
)
from .cleanup import (
    auto_cancel_expired_pending,
    cancel_booking,
    cleanup_test_booking,
    resolve_penalty_percent,
    room_rate_per_night,
)
from .collections import ensure_reservation_collections
from .lifecycle import (
    create_booking,
    get_check_in_status,
    get_room_guests,
    modify_booking,
    save_room_guests,
    validate_coupon_code,
)
from .no_show import auto_process_no_shows, process_no_show
from .queries import (
    get_booking_detail,
    get_reservation_stats,
    hotel_booking_context,
    list_bookings,
    list_reservation_dates,
)
from .validation import (
    build_reservation_input,
    validate_booking_form_requirements,
    validate_reservation_input,
)


def module_status() -> ModuleStatus:
    return ModuleStatus(
        module="reservations",
        status="partial",
        description="Solicitudes de reserva con disponibilidad, precio, teléfono huésped, historial de estados, check-in/out manual sin pagos reales.",
    )


__all__ = [
    "auto_cancel_expired_pending",
    "auto_process_no_shows",
    "build_reservation_input",
    "cancel_booking",
    "cleanup_test_booking",
    "complete_check_in",
    "complete_check_out",
    "confirm_booking",
    "create_booking",
    "ensure_reservation_collections",
    "get_booking_detail",
    "get_check_in_detail",
    "get_check_in_status",
    "get_check_out_detail",
    "get_reservation_stats",
    "get_room_guests",
    "hotel_booking_context",
    "list_bookings",
    "list_check_in_dates",
    "list_check_ins",
    "list_check_out_dates",
    "list_check_outs",
    "list_reservation_dates",
    "modify_booking",
    "module_status",
    "process_no_show",
    "reject_booking",
    "reservation_hotel_options",
    "resolve_penalty_percent",
    "room_rate_per_night",
    "save_check_in_detail",
    "save_check_out_detail",
    "save_room_guests",
    "validate_booking_form_requirements",
    "validate_coupon_code",
    "validate_reservation_input",
]
