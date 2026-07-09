"""Housekeeping lifecycle package — split into focused submodules."""

from __future__ import annotations

from .status import (
    upsert_room_status,
    list_room_status,
    get_room_status,
    update_room_status_bulk,
    sync_room_status_from_hotel_rooms,
    cleanup_orphan_room_status,
    list_valid_transitions,
)
from .cleaning_actions import (
    start_cleaning,
    complete_cleaning,
    approve_cleaning,
)
from .tasks import (
    create_housekeeping_task,
    list_housekeeping_tasks,
    complete_housekeeping_task,
    update_housekeeping_task,
    delete_housekeeping_task,
)
from .maintenance import (
    complete_maintenance_task,
    create_maintenance_task,
    list_maintenance_tasks,
    update_maintenance_task,
    delete_maintenance_task,
)
from .charges import (
    create_additional_charge,
    delete_additional_charge,
    list_additional_charges,
)
from .dashboard import get_housekeeping_dashboard, get_weekly_calendar, list_upcoming_events
from .room_history import log_room_status_change, list_room_status_history

__all__ = [
    "upsert_room_status",
    "list_room_status",
    "get_room_status",
    "update_room_status_bulk",
    "sync_room_status_from_hotel_rooms",
    "cleanup_orphan_room_status",
    "list_valid_transitions",
    "start_cleaning",
    "complete_cleaning",
    "approve_cleaning",
    "log_room_status_change",
    "list_room_status_history",
    "create_housekeeping_task",
    "list_housekeeping_tasks",
    "complete_housekeeping_task",
    "update_housekeeping_task",
    "delete_housekeeping_task",
    "complete_maintenance_task",
    "create_maintenance_task",
    "list_maintenance_tasks",
    "update_maintenance_task",
    "delete_maintenance_task",
    "create_additional_charge",
    "delete_additional_charge",
    "list_additional_charges",
    "get_housekeeping_dashboard",
    "get_weekly_calendar",
    "list_upcoming_events",
]
