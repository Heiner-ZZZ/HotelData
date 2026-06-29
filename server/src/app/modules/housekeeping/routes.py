from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from src.app.modules.housekeeping.schemas import (
    AdditionalChargeCreate,
    HousekeepingTaskCreate,
    MaintenanceTaskCreate,
    ModuleStatus,
    RoomStatusLogCreate,
)
from src.app.modules.housekeeping.service import (
    approve_cleaning,
    complete_cleaning,
    complete_housekeeping_task,
    complete_maintenance_task,
    create_additional_charge,
    create_housekeeping_task,
    create_maintenance_task,
    delete_housekeeping_task,
    delete_maintenance_task,
    get_housekeeping_dashboard,
    get_room_status,
    list_additional_charges,
    list_housekeeping_tasks,
    list_maintenance_tasks,
    list_room_status,
    list_room_status_history,
    list_upcoming_events,
    list_valid_transitions,
    module_status,
    start_cleaning,
    sync_room_status_from_hotel_rooms,
    update_housekeeping_task,
    update_maintenance_task,
    update_room_status_bulk,
    upsert_room_status,
)
from src.app.security.dependencies import require_login

router = APIRouter(prefix="/modules/housekeeping", tags=["modules-housekeeping"])
api_router = APIRouter(prefix="/api/housekeeping", tags=["housekeeping-api"])


@router.get("/status", response_model=ModuleStatus)
def housekeeping_module_status() -> ModuleStatus:
    return module_status()


# ═══════════════════════════════════════════════
# Room Status
# ═══════════════════════════════════════════════


@api_router.put("/room-status", status_code=200)
def room_status_upsert_api(
    payload: RoomStatusLogCreate = Body(...),
    current_user: dict = Depends(require_login),
):
    """Create or update a room's status."""
    return upsert_room_status(payload)


@api_router.get("/room-status")
def room_status_list_api(
    prop_id: int | None = Query(default=None, ge=1),
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(require_login),
):
    """List room statuses with optional filtering."""
    return list_room_status(
        prop_id=prop_id,
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )


@api_router.get("/room-status/{record_id}")
def room_status_get_api(
    record_id: str,
    current_user: dict = Depends(require_login),
):
    """Get a single room status record."""
    result = get_room_status(record_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro no encontrado")
    return result


@api_router.post("/room-status/bulk")
def room_status_bulk_api(
    payload: dict = Body(...),
    current_user: dict = Depends(require_login),
):
    """Update status for multiple rooms at once."""
    prop_id = payload.get("prop_id")
    room_labels = payload.get("room_labels", [])
    new_status = payload.get("status", "available")
    note = payload.get("note", "")
    if not prop_id or not room_labels:
        raise HTTPException(status_code=400, detail="prop_id y room_labels son requeridos")
    count = update_room_status_bulk(prop_id, room_labels, new_status, note)
    return {"ok": True, "updated_count": count}


@api_router.post("/room-status/sync")
def room_status_sync_api(
    payload: dict = Body(...),
    current_user: dict = Depends(require_login),
):
    """Auto‑seed room_status_log from hotel_rooms for a property."""
    prop_id = payload.get("prop_id")
    if not prop_id:
        raise HTTPException(status_code=400, detail="prop_id es requerido")
    return sync_room_status_from_hotel_rooms(prop_id)


# ═══════════════════════════════════════════════
# Housekeeping Tasks
# ═══════════════════════════════════════════════


@api_router.post("/tasks", status_code=201)
def hk_task_create_api(
    payload: HousekeepingTaskCreate = Body(...),
    current_user: dict = Depends(require_login),
):
    """Create a new housekeeping task."""
    return create_housekeeping_task(payload)


@api_router.get("/tasks")
def hk_task_list_api(
    prop_id: int | None = Query(default=None, ge=1),
    status_filter: str | None = Query(default=None, alias="status"),
    assigned_to: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_login),
):
    """List housekeeping tasks."""
    return list_housekeeping_tasks(
        prop_id=prop_id,
        status_filter=status_filter,
        assigned_to=assigned_to,
        page=page,
        page_size=page_size,
    )


@api_router.post("/tasks/{task_id}/complete")
def hk_task_complete_api(
    task_id: str,
    payload: dict = Body(default={}),
    current_user: dict = Depends(require_login),
):
    """Mark a housekeeping task as completed."""
    result = complete_housekeeping_task(task_id, note=str(payload.get("note", "")))
    if result is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada o ya completada")
    return result


@api_router.put("/tasks/{task_id}")
def hk_task_update_api(
    task_id: str,
    payload: HousekeepingTaskCreate = Body(...),
    current_user: dict = Depends(require_login),
):
    """Update a housekeeping task."""
    result = update_housekeeping_task(task_id, payload)
    if result is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return result


@api_router.delete("/tasks/{task_id}")
def hk_task_delete_api(
    task_id: str,
    current_user: dict = Depends(require_login),
):
    """Logically delete a housekeeping task."""
    result = delete_housekeeping_task(task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada o ya eliminada")
    return result


# ═══════════════════════════════════════════════
# Maintenance
# ═══════════════════════════════════════════════


@api_router.post("/maintenance", status_code=201)
def mt_task_create_api(
    payload: MaintenanceTaskCreate = Body(...),
    current_user: dict = Depends(require_login),
):
    """Create a new maintenance task."""
    return create_maintenance_task(payload)


@api_router.get("/maintenance")
def mt_task_list_api(
    prop_id: int | None = Query(default=None, ge=1),
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_login),
):
    """List maintenance tasks."""
    return list_maintenance_tasks(
        prop_id=prop_id,
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )


@api_router.put("/maintenance/{task_id}")
def mt_task_update_api(
    task_id: str,
    payload: MaintenanceTaskCreate = Body(...),
    current_user: dict = Depends(require_login),
):
    """Update a maintenance task."""
    result = update_maintenance_task(task_id, payload)
    if result is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    return result


@api_router.post("/maintenance/{task_id}/complete")
def mt_task_complete_api(
    task_id: str,
    payload: dict = Body(default={}),
    current_user: dict = Depends(require_login),
):
    """Mark a maintenance task as completed."""
    result = complete_maintenance_task(task_id, note=str(payload.get("note", "")))
    if result is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada o ya completada")
    return result


@api_router.delete("/maintenance/{task_id}")
def mt_task_delete_api(
    task_id: str,
    current_user: dict = Depends(require_login),
):
    """Logically delete a maintenance task."""
    result = delete_maintenance_task(task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada o ya eliminada")
    return result


# ═══════════════════════════════════════════════
# Additional Charges
# ═══════════════════════════════════════════════


@api_router.post("/charges", status_code=201)
def charge_create_api(
    payload: AdditionalChargeCreate = Body(...),
    current_user: dict = Depends(require_login),
):
    """Register an additional charge against a booking."""
    result = create_additional_charge(payload)
    if result is None:
        raise HTTPException(status_code=400, detail="No se pudo crear el cargo (booking inválido)")
    return result


@api_router.get("/charges")
def charge_list_api(
    booking_id: str | None = Query(default=None),
    prop_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_login),
):
    """List additional charges."""
    return list_additional_charges(
        booking_id=booking_id,
        prop_id=prop_id,
        page=page,
        page_size=page_size,
    )


# ═══════════════════════════════════════════════
# Room Status History / Audit Trail
# ═══════════════════════════════════════════════


@api_router.get("/room-status/history")
def room_status_history_api(
    prop_id: int | None = Query(default=None, ge=1),
    room_label: str | None = Query(default=None),
    booking_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(require_login),
):
    """List room status change history for auditing."""
    return list_room_status_history(
        prop_id=prop_id,
        room_label=room_label,
        booking_id=booking_id,
        page=page,
        page_size=page_size,
    )


# ═══════════════════════════════════════════════
# Room Status Transitions & Cleaning Actions
# ═══════════════════════════════════════════════


@api_router.get("/room-status/transitions")
def room_status_transitions_api(
    current_status: str | None = Query(default=None),
    current_user: dict = Depends(require_login),
):
    """Return valid transitions for the housekeeping cycle.
    If current_status is provided, returns only valid next statuses.
    """
    return list_valid_transitions(status=current_status)


@api_router.post("/cleaning/start")
def cleaning_start_api(
    payload: dict = Body(...),
    current_user: dict = Depends(require_login),
):
    """Start a cleaning session. Marks room as cleaning_in_progress.

    Payload:
    {
      "prop_id": 42,
      "room_label": "1201",
      "assigned_to": "María",
      "task_id": "optional"
    }
    """
    prop_id = int(payload.get("prop_id", 0))
    room_label = payload.get("room_label", "")
    if not prop_id or not room_label:
        raise HTTPException(status_code=400, detail="prop_id y room_label son requeridos")
    result = start_cleaning(
        prop_id, room_label,
        assigned_to=payload.get("assigned_to", ""),
        task_id=payload.get("task_id"),
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Habitación no encontrada")
    return result


@api_router.post("/cleaning/complete")
def cleaning_complete_api(
    payload: dict = Body(...),
    current_user: dict = Depends(require_login),
):
    """Complete a cleaning session with the housekeeper's report.

    Payload:
    {
      "prop_id": 42,
      "room_label": "1201",
      "assigned_to": "María",
      "observations": "Toallas cambiadas, piso trapeado",
      "damage_found": false,
      "damage_description": "",
      "lost_object_found": false,
      "lost_object_description": "",
      "needs_maintenance": false,
      "maintenance_description": ""
    }

    If damage_found or needs_maintenance → auto-creates maintenance task
    and blocks the room. If lost_object_found → auto-creates Lost & Found entry.
    """
    prop_id = int(payload.get("prop_id", 0))
    room_label = payload.get("room_label", "")
    if not prop_id or not room_label:
        raise HTTPException(status_code=400, detail="prop_id y room_label son requeridos")
    result = complete_cleaning(
        prop_id, room_label,
        assigned_to=payload.get("assigned_to", ""),
        observations=payload.get("observations", ""),
        damage_found=bool(payload.get("damage_found", False)),
        damage_description=payload.get("damage_description", ""),
        lost_object_found=bool(payload.get("lost_object_found", False)),
        lost_object_description=payload.get("lost_object_description", ""),
        needs_maintenance=bool(payload.get("needs_maintenance", False)),
        maintenance_description=payload.get("maintenance_description", ""),
    )
    return result


@api_router.post("/cleaning/approve")
def cleaning_approve_api(
    payload: dict = Body(...),
    current_user: dict = Depends(require_login),
):
    """Supervisor approves the cleaning → room becomes vacant_clean.

    Payload:
    {
      "prop_id": 42,
      "room_label": "1201",
      "inspected_by": "supervisor_name",
      "note": "Todo en orden",
      "set_occupied": false  // true si el huésped ya está dentro
    }
    """
    prop_id = int(payload.get("prop_id", 0))
    room_label = payload.get("room_label", "")
    if not prop_id or not room_label:
        raise HTTPException(status_code=400, detail="prop_id y room_label son requeridos")
    result = approve_cleaning(
        prop_id, room_label,
        inspected_by=payload.get("inspected_by", "supervisor"),
        note=payload.get("note", ""),
        set_occupied=bool(payload.get("set_occupied", False)),
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Habitación no encontrada")
    return result


# ═══════════════════════════════════════════════
# Dashboard
# ═══════════════════════════════════════════════


@api_router.get("/dashboard")
def housekeeping_dashboard_api(
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_login),
):
    """Return aggregated KPIs for housekeeping efficiency monitoring (CU-E09)."""
    return get_housekeeping_dashboard(prop_id=prop_id)


@api_router.get("/upcoming-events")
def upcoming_events_api(
    prop_id: int | None = Query(default=None, ge=1),
    days: int = Query(default=30, ge=1, le=90),
    current_user: dict = Depends(require_login),
):
    """Return upcoming tasks and maintenance events for calendar display."""
    return list_upcoming_events(prop_id=prop_id, days=days)
