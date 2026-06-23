from __future__ import annotations

from src.app.modules.reservations.schemas import ModuleStatus
from .validation import validate_reservation_input, build_reservation_input
from .collections import ensure_reservation_collections
from .queries import hotel_booking_context, list_bookings, get_booking_detail, list_reservation_dates
from ._hotel_options import reservation_hotel_options
from .lifecycle import create_booking
from .cleanup import cancel_booking, cleanup_test_booking
from ._view_ops import list_check_ins, list_check_outs, list_check_in_dates, list_check_out_dates
from ._checkinout import complete_check_in, complete_check_out


def module_status() -> ModuleStatus:
    return ModuleStatus(
        module="reservations",
        status="partial",
        description="Core minimo de solicitudes de reserva con detalle, cancelacion e ingreso manual sin pagos reales.",
    )


__all__ = [
    "module_status",
    "ensure_reservation_collections",
    "validate_reservation_input",
    "build_reservation_input",
    "hotel_booking_context",
    "reservation_hotel_options",
    "create_booking",
    "list_bookings",
    "get_booking_detail",
    "list_reservation_dates",
    "cancel_booking",
    "cleanup_test_booking",
    "list_check_ins",
    "list_check_outs",
    "list_check_in_dates",
    "list_check_out_dates",
    "complete_check_in",
    "complete_check_out",
]
