from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status

from src.app.modules.housekeeping.schemas import (
    AdditionalChargeCreate,
    AdditionalChargeUpdate,
    HousekeepingTaskCreate,
    MaintenanceTaskCreate,
    ModuleStatus,
    RoomStatusLogCreate,
)
from src.app.modules.housekeeping.service import (
    approve_cleaning,
    cleanup_orphan_room_status,
    complete_cleaning,
    complete_housekeeping_task,
    complete_maintenance_task,
    create_additional_charge,
    create_housekeeping_task,
    create_maintenance_task,
    delete_additional_charge,
    delete_housekeeping_task,
    delete_maintenance_task,
    get_housekeeping_dashboard,
    get_room_status,
    get_weekly_calendar,
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
    update_additional_charge,
    update_housekeeping_task,
    update_maintenance_task,
    update_room_status_bulk,
    upsert_room_status,
)
from src.app.modules.housekeeping.routes_impl import (
    extract_cleaning_approve_params,
    extract_cleaning_complete_params,
    extract_cleaning_start_params,
    query_housekeeping_staff,
    validate_bulk_update,
    validate_sync_payload,
)
from src.app.modules.partner.services.audit import register_action
from src.app.security.dependencies import require_login, require_permission

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
    current_user: dict = Depends(require_permission("housekeeping.create")),
):
    """Create or update a room's status."""
    from src.database.connection import get_database
    db = get_database()
    from .service.collections import ROOM_STATUS_COLLECTION
    before = db[ROOM_STATUS_COLLECTION].find_one(
        {"prop_id": payload.prop_id, "room_label": payload.room_label},
        {"status": 1},
    )
    result = upsert_room_status(payload)
    diff = {
        "status": {
            "old": before.get("status") if before else None,
            "new": payload.status,
        },
    }
    register_action(
        prop_id=payload.prop_id,
        entity_type="housekeeping_room_status",
        entity_id=f"{payload.prop_id}:{payload.room_label}",
        action="update" if before else "create",
        summary=f"{'Actualización' if before else 'Creación'} de estado de habitación {payload.room_label} → {payload.status}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    return result


@api_router.get("/room-status")
def room_status_list_api(
    request: Request,
    prop_id: int | None = Query(default=None, ge=1),
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(require_permission("housekeeping.read")),
):
    """List room statuses with optional filtering."""
    result = list_room_status(
        prop_id=prop_id,
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )
    register_action(
        prop_id=prop_id or 0,
        entity_type="housekeeping_room_status",
        entity_id="list",
        action="read",
        summary=f"Listado de estados de habitación (total={result.get('total', 0)}, page={page})",
        changed_by=current_user.get("username", "system"),
        metadata={"prop_id": prop_id, "status": status_filter, "page": page, "url": str(request.url)},
    )
    return result


@api_router.get("/room-status/history")
def room_status_history_api(
    request: Request,
    prop_id: int | None = Query(default=None, ge=1),
    room_label: str | None = Query(default=None),
    booking_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(require_permission("housekeeping.read")),
):
    """List room status change history for auditing."""
    result = list_room_status_history(
        prop_id=prop_id,
        room_label=room_label,
        booking_id=booking_id,
        page=page,
        page_size=page_size,
    )
    register_action(
        prop_id=prop_id or 0,
        entity_type="housekeeping_room_status",
        entity_id="history",
        action="read",
        summary=f"Historial de estados de habitación (page={page})",
        changed_by=current_user.get("username", "system"),
        metadata={"prop_id": prop_id, "room_label": room_label, "booking_id": booking_id, "url": str(request.url)},
    )
    return result


@api_router.get("/room-status/{record_id}")
def room_status_get_api(
    request: Request,
    record_id: str,
    current_user: dict = Depends(require_permission("housekeeping.read")),
):
    """Get a single room status record."""
    result = get_room_status(record_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro no encontrado")
    register_action(
        prop_id=result.get("propId", 0),
        entity_type="housekeeping_room_status",
        entity_id=record_id,
        action="read",
        summary=f"Consulta de estado de habitación {result.get('roomLabel', record_id)}",
        changed_by=current_user.get("username", "system"),
        metadata={"url": str(request.url)},
    )
    return result


@api_router.post("/room-status/bulk")
def room_status_bulk_api(
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("housekeeping.update")),
):
    """Update status for multiple rooms at once."""
    prop_id, room_labels, new_status, note = validate_bulk_update(payload)
    count = update_room_status_bulk(prop_id, room_labels, new_status, note)
    register_action(
        prop_id=prop_id or 0,
        entity_type="housekeeping_room_status",
        entity_id="bulk",
        action="update",
        summary=f"Actualización masiva de estados: {count} habitación(es) → {new_status}",
        changed_by=current_user.get("username", "system"),
        diff={
            "rooms": {"old": None, "new": room_labels},
            "status": {"old": None, "new": new_status},
        },
    )
    return {"ok": True, "updated_count": count}


@api_router.post("/room-status/sync")
def room_status_sync_api(
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("housekeeping.update")),
):
    """Auto‑seed room_status_log from hotel_rooms for a property."""
    prop_id = validate_sync_payload(payload)
    result = sync_room_status_from_hotel_rooms(prop_id)
    register_action(
        prop_id=prop_id or 0,
        entity_type="housekeeping_room_status",
        entity_id="sync",
        action="update",
        summary=f"Sincronización de estados de habitación: {result.get('created', 0)} creadas",
        changed_by=current_user.get("username", "system"),
        diff={"created": {"old": None, "new": result.get("created", 0)}},
    )
    return result


@api_router.post("/room-status/cleanup-orphans")
def room_status_cleanup_api(
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("housekeeping.delete")),
):
    """Remove orphaned room_status_log entries whose hotel_room_id or
    room_type_id no longer exist in hotel_rooms or room_types.

    Payload: {"prop_id": 1}  (optional; if omitted, cleans all properties)
    """
    prop_id = payload.get("prop_id") if payload.get("prop_id") else None
    result = cleanup_orphan_room_status(prop_id=prop_id)
    register_action(
        prop_id=prop_id or 0,
        entity_type="housekeeping_room_status",
        entity_id="cleanup_orphans",
        action="delete",
        summary=f"Limpieza de registros huérfanos: {result.get('deleted', 0)} eliminados",
        changed_by=current_user.get("username", "system"),
        diff={
            "deleted": {"old": None, "new": result.get("deleted", 0)},
            "orphaned_summary": {"old": None, "new": result.get("orphaned_summary", {})},
        },
    )
    return result


# ═══════════════════════════════════════════════
# Housekeeping Tasks
# ═══════════════════════════════════════════════


@api_router.post("/tasks", status_code=201)
def hk_task_create_api(
    payload: HousekeepingTaskCreate = Body(...),
    current_user: dict = Depends(require_permission("housekeeping.create")),
):
    """Create a new housekeeping task."""
    try:
        result = create_housekeeping_task(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    diff = {
        k: {"old": None, "new": v}
        for k, v in result.items()
        if k not in ("id", "created_at", "completed_at") and v is not None
    }
    register_action(
        prop_id=result.get("propId", payload.prop_id),
        entity_type="housekeeping_task",
        entity_id=result.get("id", ""),
        action="create",
        summary=f"Creación de tarea de limpieza: {payload.task_type} — Hab. {result.get('roomLabel', '')}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    return result


@api_router.get("/tasks")
def hk_task_list_api(
    request: Request,
    prop_id: int | None = Query(default=None, ge=1),
    status_filter: str | None = Query(default=None, alias="status"),
    assigned_to: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_permission("housekeeping.read")),
):
    """List housekeeping tasks."""
    result = list_housekeeping_tasks(
        prop_id=prop_id,
        status_filter=status_filter,
        assigned_to=assigned_to,
        priority=priority,
        page=page,
        page_size=page_size,
    )
    register_action(
        prop_id=prop_id or 0,
        entity_type="housekeeping_task",
        entity_id="list",
        action="read",
        summary=f"Listado de tareas de limpieza (total={result.get('total', 0)}, page={page})",
        changed_by=current_user.get("username", "system"),
        metadata={"prop_id": prop_id, "status": status_filter, "assigned_to": assigned_to, "url": str(request.url)},
    )
    return result


@api_router.post("/tasks/{task_id}/complete")
def hk_task_complete_api(
    task_id: str,
    payload: dict = Body(default={}),
    current_user: dict = Depends(require_permission("housekeeping.update")),
):
    """Mark a housekeeping task as completed."""
    from src.database.connection import get_database
    from bson import ObjectId
    from bson.errors import InvalidId
    db = get_database()
    try:
        before = db.housekeeping_tasks.find_one({"_id": ObjectId(task_id)}, {"status": 1, "prop_id": 1, "room_label": 1, "task_type": 1})
    except (InvalidId, Exception):
        before = None
    result = complete_housekeeping_task(task_id, note=str(payload.get("note", "")))
    if result is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada o ya completada")
    diff = {
        "status": {"old": before.get("status") if before else None, "new": "completed"},
    }
    register_action(
        prop_id=(before.get("prop_id") or 0) if before else 0,
        entity_type="housekeeping_task",
        entity_id=task_id,
        action="update",
        summary=f"Completado de tarea de limpieza {task_id} — Hab. {result.get('roomLabel', '')}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    return result


@api_router.put("/tasks/{task_id}")
def hk_task_update_api(
    task_id: str,
    payload: HousekeepingTaskCreate = Body(...),
    current_user: dict = Depends(require_permission("housekeeping.update")),
):
    """Update a housekeeping task."""
    from src.database.connection import get_database
    from bson import ObjectId
    from bson.errors import InvalidId
    db = get_database()
    try:
        before = db.housekeeping_tasks.find_one(
            {"_id": ObjectId(task_id)},
            {"prop_id": 1, "room_id": 1, "room_label": 1, "task_type": 1, "status": 1, "assigned_to": 1, "priority": 1, "note": 1, "scheduled_date": 1},
        )
    except (InvalidId, Exception):
        before = None
    try:
        result = update_housekeeping_task(task_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if result is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    diff = {}
    for key in ["room_id", "task_type", "status", "assigned_to", "priority", "note", "scheduled_date"]:
        old_val = before.get(key) if before else None
        new_val = getattr(payload, key, None)
        if old_val != new_val:
            diff[key] = {"old": old_val, "new": new_val}
    register_action(
        prop_id=(before.get("prop_id") or 0) if before else payload.prop_id,
        entity_type="housekeeping_task",
        entity_id=task_id,
        action="update",
        summary=f"Actualización de tarea de limpieza {task_id} — Hab. {result.get('roomLabel', '')}",
        changed_by=current_user.get("username", "system"),
        diff=diff if diff else None,
    )
    return result


@api_router.delete("/tasks/{task_id}")
def hk_task_delete_api(
    task_id: str,
    current_user: dict = Depends(require_permission("housekeeping.delete")),
):
    """Logically delete a housekeeping task."""
    result = delete_housekeeping_task(task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada o ya eliminada")
    register_action(
        prop_id=result.get("prop_id", 0),
        entity_type="housekeeping_task",
        entity_id=task_id,
        action="delete",
        summary=f"Eliminación lógica de tarea de limpieza {task_id} — Hab. {result.get('roomLabel', '')}",
        changed_by=current_user.get("username", "system"),
        diff={"status": {"old": result.get("status") if result else None, "new": "deleted"}},
    )
    return result


# ═══════════════════════════════════════════════
# Maintenance
# ═══════════════════════════════════════════════


@api_router.post("/maintenance", status_code=201)
def mt_task_create_api(
    payload: MaintenanceTaskCreate = Body(...),
    current_user: dict = Depends(require_permission("maintenance.manage")),
):
    """Create a new maintenance task."""
    try:
        result = create_maintenance_task(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    diff = {
        k: {"old": None, "new": v}
        for k, v in result.items()
        if k not in ("id", "created_at", "completed_at") and v is not None
    }
    register_action(
        prop_id=result.get("propId", payload.prop_id),
        entity_type="housekeeping_maintenance",
        entity_id=result.get("id", ""),
        action="create",
        summary=f"Creación de tarea de mantenimiento: {payload.title} — Hab. {result.get('roomLabel', '')}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    return result


@api_router.get("/maintenance")
def mt_task_list_api(
    request: Request,
    prop_id: int | None = Query(default=None, ge=1),
    status_filter: str | None = Query(default=None, alias="status"),
    priority: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_permission("maintenance.read")),
):
    """List maintenance tasks."""
    result = list_maintenance_tasks(
        prop_id=prop_id,
        status_filter=status_filter,
        priority=priority,
        page=page,
        page_size=page_size,
    )
    register_action(
        prop_id=prop_id or 0,
        entity_type="housekeeping_maintenance",
        entity_id="list",
        action="read",
        summary=f"Listado de tareas de mantenimiento (total={result.get('total', 0)}, page={page})",
        changed_by=current_user.get("username", "system"),
        metadata={"prop_id": prop_id, "status": status_filter, "url": str(request.url)},
    )
    return result


@api_router.put("/maintenance/{task_id}")
def mt_task_update_api(
    task_id: str,
    payload: MaintenanceTaskCreate = Body(...),
    current_user: dict = Depends(require_permission("maintenance.update")),
):
    """Update a maintenance task."""
    from src.database.connection import get_database
    from bson import ObjectId
    from bson.errors import InvalidId
    db = get_database()
    try:
        before = db.maintenance_tasks.find_one(
            {"_id": ObjectId(task_id)},
            {"prop_id": 1, "room_id": 1, "room_label": 1, "title": 1, "status": 1, "priority": 1, "task_type": 1, "scheduled_date": 1},
        )
    except (InvalidId, Exception):
        before = None
    try:
        result = update_maintenance_task(task_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if result is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    diff = {}
    for key in ["room_id", "title", "status", "priority", "task_type", "scheduled_date"]:
        old_val = before.get(key) if before else None
        new_val = getattr(payload, key, None)
        if old_val != new_val:
            diff[key] = {"old": old_val, "new": new_val}
    register_action(
        prop_id=(before.get("prop_id") or 0) if before else payload.prop_id,
        entity_type="housekeeping_maintenance",
        entity_id=task_id,
        action="update",
        summary=f"Actualización de tarea de mantenimiento {task_id} — {result.get('title', '')}",
        changed_by=current_user.get("username", "system"),
        diff=diff if diff else None,
    )
    return result


@api_router.post("/maintenance/{task_id}/complete")
def mt_task_complete_api(
    task_id: str,
    payload: dict = Body(default={}),
    current_user: dict = Depends(require_permission("maintenance.update")),
):
    """Mark a maintenance task as completed."""
    from src.database.connection import get_database
    from bson import ObjectId
    from bson.errors import InvalidId
    db = get_database()
    try:
        before = db.maintenance_tasks.find_one({"_id": ObjectId(task_id)}, {"status": 1, "prop_id": 1, "room_label": 1, "title": 1})
    except (InvalidId, Exception):
        before = None
    result = complete_maintenance_task(task_id, note=str(payload.get("note", "")))
    if result is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada o ya completada")
    diff = {
        "status": {"old": before.get("status") if before else None, "new": "completed"},
    }
    register_action(
        prop_id=(before.get("prop_id") or 0) if before else 0,
        entity_type="housekeeping_maintenance",
        entity_id=task_id,
        action="update",
        summary=f"Completado de tarea de mantenimiento {task_id} — {result.get('title', '')}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    return result


@api_router.delete("/maintenance/{task_id}")
def mt_task_delete_api(
    task_id: str,
    current_user: dict = Depends(require_permission("maintenance.manage")),
):
    """Logically delete a maintenance task."""
    result = delete_maintenance_task(task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Tarea no encontrada o ya eliminada")
    register_action(
        prop_id=result.get("prop_id", 0),
        entity_type="housekeeping_maintenance",
        entity_id=task_id,
        action="delete",
        summary=f"Eliminación lógica de tarea de mantenimiento {task_id} — {result.get('title', '')}",
        changed_by=current_user.get("username", "system"),
        diff={"status": {"old": result.get("status") if result else None, "new": "deleted"}},
    )
    return result


# ═══════════════════════════════════════════════
# Additional Charges
# ═══════════════════════════════════════════════


@api_router.post("/charges", status_code=201)
def charge_create_api(
    payload: AdditionalChargeCreate = Body(...),
    current_user: dict = Depends(require_permission("charges.manage")),
):
    """Register an additional charge against a booking."""
    result = create_additional_charge(payload)
    if result is None:
        raise HTTPException(status_code=400, detail="No se pudo crear el cargo (booking inválido)")
    diff = {
        k: {"old": None, "new": v}
        for k, v in result.items()
        if k not in ("id", "created_at") and v is not None
    }
    register_action(
        prop_id=result.get("prop_id", payload.prop_id),
        entity_type="housekeeping_charge",
        entity_id=result.get("id", ""),
        action="create",
        summary=f"Cargo adicional: {payload.concept} — ${payload.amount}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    return result


@api_router.get("/charges")
def charge_list_api(
    request: Request,
    booking_id: str | None = Query(default=None),
    prop_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_permission("charges.read")),
):
    """List additional charges."""
    result = list_additional_charges(
        booking_id=booking_id,
        prop_id=prop_id,
        page=page,
        page_size=page_size,
    )
    register_action(
        prop_id=prop_id or 0,
        entity_type="housekeeping_charge",
        entity_id="list",
        action="read",
        summary=f"Listado de cargos adicionales (total={result.get('total', 0)}, page={page})",
        changed_by=current_user.get("username", "system"),
        metadata={"booking_id": booking_id, "prop_id": prop_id, "url": str(request.url)},
    )
    return result


@api_router.delete("/charges/{charge_id}")
def charge_delete_api(
    charge_id: str,
    current_user: dict = Depends(require_permission("charges.manage")),
):
    """Delete an additional charge (e.g., added by mistake)."""
    result = delete_additional_charge(charge_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Cargo no encontrado")
    register_action(
        prop_id=0,
        entity_type="housekeeping_charge",
        entity_id=charge_id,
        action="delete",
        summary=f"Eliminación de cargo adicional {charge_id} — booking {result.get('booking_id', '')}",
        changed_by=current_user.get("username", "system"),
        diff={"deleted_id": {"old": None, "new": charge_id}},
    )
    return result


@api_router.put("/charges/{charge_id}")
def charge_update_api(
    charge_id: str,
    payload: AdditionalChargeUpdate = Body(...),
    current_user: dict = Depends(require_permission("charges.manage")),
):
    """Update an additional charge. Only allowed if created today (same calendar day)."""
    result = update_additional_charge(charge_id, payload)
    if result is None:
        raise HTTPException(
            status_code=400,
            detail="No se pudo actualizar: el cargo no existe o fue creado en otro día.",
        )
    register_action(
        prop_id=result.get("prop_id", 0),
        entity_type="housekeeping_charge",
        entity_id=charge_id,
        action="update",
        summary=f"Actualización de cargo adicional {charge_id} — {result.get('concept', '')}",
        changed_by=current_user.get("username", "system"),
    )
    return result


# ═══════════════════════════════════════════════
# Room Status Transitions & Cleaning Actions
# ═══════════════════════════════════════════════


@api_router.get("/room-status/transitions")
def room_status_transitions_api(
    request: Request,
    current_status: str | None = Query(default=None),
    current_user: dict = Depends(require_permission("housekeeping.read")),
):
    """Return valid transitions for the housekeeping cycle.
    If current_status is provided, returns only valid next statuses.
    """
    result = list_valid_transitions(status=current_status)
    register_action(
        prop_id=0,
        entity_type="housekeeping_room_status",
        entity_id="transitions",
        action="read",
        summary="Consulta de transiciones de estado válidas",
        changed_by=current_user.get("username", "system"),
        metadata={"current_status": current_status, "url": str(request.url)},
    )
    return result


@api_router.post("/cleaning/start")
def cleaning_start_api(
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("housekeeping.update")),
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
    prop_id, room_label, assigned_to, task_id = extract_cleaning_start_params(payload)
    from src.database.connection import get_database
    from .service.collections import ROOM_STATUS_COLLECTION
    db = get_database()
    before = db[ROOM_STATUS_COLLECTION].find_one(
        {"prop_id": prop_id, "room_label": room_label},
        {"status": 1},
    )
    result = start_cleaning(prop_id, room_label, assigned_to=assigned_to, task_id=task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Habitación no encontrada")
    diff = {
        "status": {"old": before.get("status") if before else None, "new": "cleaning_in_progress"},
    }
    register_action(
        prop_id=prop_id,
        entity_type="housekeeping_cleaning",
        entity_id=f"{prop_id}:{room_label}",
        action="update",
        summary=f"Inicio de limpieza — Hab. {room_label} (asignado a {assigned_to or 'no asignado'})",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    return result


@api_router.post("/cleaning/complete")
def cleaning_complete_api(
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("housekeeping.update")),
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
    cp = extract_cleaning_complete_params(payload)
    from src.database.connection import get_database
    from .service.collections import ROOM_STATUS_COLLECTION
    db = get_database()
    before = db[ROOM_STATUS_COLLECTION].find_one(
        {"prop_id": cp["prop_id"], "room_label": cp["room_label"]},
        {"status": 1},
    )
    result = complete_cleaning(
        cp["prop_id"], cp["room_label"],
        assigned_to=cp["assigned_to"], observations=cp["observations"],
        damage_found=cp["damage_found"], damage_description=cp["damage_description"],
        lost_object_found=cp["lost_object_found"], lost_object_description=cp["lost_object_description"],
        needs_maintenance=cp["needs_maintenance"], maintenance_description=cp["maintenance_description"],
    )
    new_status = result.get("status", "cleaning_completed") if isinstance(result, dict) else "cleaning_completed"
    diff = {
        "status": {"old": before.get("status") if before else None, "new": new_status},
    }
    register_action(
        prop_id=cp["prop_id"],
        entity_type="housekeeping_cleaning",
        entity_id=f"{cp['prop_id']}:{cp['room_label']}",
        action="update",
        summary=f"Completado de limpieza — Hab. {cp['room_label']} → {new_status}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    return result


@api_router.post("/cleaning/approve")
def cleaning_approve_api(
    payload: dict = Body(...),
    current_user: dict = Depends(require_permission("housekeeping.update")),
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
    prop_id, room_label, inspected_by, note, set_occupied = extract_cleaning_approve_params(payload)
    from src.database.connection import get_database
    from .service.collections import ROOM_STATUS_COLLECTION
    db = get_database()
    before = db[ROOM_STATUS_COLLECTION].find_one(
        {"prop_id": prop_id, "room_label": room_label},
        {"status": 1},
    )
    result = approve_cleaning(prop_id, room_label, inspected_by=inspected_by, note=note, set_occupied=set_occupied)
    if result is None:
        raise HTTPException(status_code=404, detail="Habitación no encontrada")
    new_status = result.get("status", "vacant_clean")
    diff = {
        "status": {"old": before.get("status") if before else None, "new": new_status},
    }
    register_action(
        prop_id=prop_id,
        entity_type="housekeeping_cleaning",
        entity_id=f"{prop_id}:{room_label}",
        action="update",
        summary=f"Aprobación de limpieza — Hab. {room_label} → {new_status} (por {inspected_by})",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    return result


# ═══════════════════════════════════════════════
# Dashboard
# ═══════════════════════════════════════════════


@api_router.get("/dashboard")
def housekeeping_dashboard_api(
    request: Request,
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_permission("housekeeping.read")),
):
    """Return aggregated KPIs for housekeeping efficiency monitoring (CU-E09)."""
    result = get_housekeeping_dashboard(prop_id=prop_id)
    register_action(
        prop_id=prop_id or 0,
        entity_type="housekeeping_dashboard",
        entity_id="dashboard",
        action="read",
        summary="Consulta de dashboard de housekeeping",
        changed_by=current_user.get("username", "system"),
        metadata={"prop_id": prop_id, "url": str(request.url)},
    )
    return result


@api_router.get("/calendar-week")
def weekly_calendar_api(
    request: Request,
    prop_id: int = Query(..., ge=1, description="Property ID"),
    week_start: str = Query(..., description="Start date in YYYY-MM-DD format"),
    assigned_to: str | None = Query(default=None, description="Filter by staff name"),
    current_user: dict = Depends(require_permission("housekeeping.read")),
):
    """Return a weekly calendar grid: rooms × days with scheduled tasks and maintenance events.

    Each room shows its current status and scheduled tasks for each day of the week.
    Supports filtering by assigned staff.
    """
    result = get_weekly_calendar(
        prop_id=prop_id,
        week_start=week_start,
        assigned_to=assigned_to,
    )
    register_action(
        prop_id=prop_id,
        entity_type="housekeeping_calendar",
        entity_id="weekly",
        action="read",
        summary=f"Consulta de calendario semanal desde {week_start}",
        changed_by=current_user.get("username", "system"),
        metadata={"prop_id": prop_id, "week_start": week_start, "assigned_to": assigned_to, "url": str(request.url)},
    )
    return result


@api_router.get("/staff")
def housekeeping_staff_api(
    request: Request,
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_permission("housekeeping.read")),
):
    """Return staff users assigned to a property who have maintenance/housekeeping roles."""
    staff = query_housekeeping_staff(prop_id=prop_id)
    register_action(
        prop_id=prop_id or 0,
        entity_type="housekeeping_staff",
        entity_id="staff_list",
        action="read",
        summary=f"Consulta de personal de housekeeping (prop_id={prop_id})",
        changed_by=current_user.get("username", "system"),
        metadata={"prop_id": prop_id, "url": str(request.url)},
    )
    return {"staff": staff}


@api_router.get("/upcoming-events")
def upcoming_events_api(
    request: Request,
    prop_id: int | None = Query(default=None, ge=1),
    days: int = Query(default=30, ge=1, le=90),
    current_user: dict = Depends(require_permission("housekeeping.read")),
):
    """Return upcoming tasks and maintenance events for calendar display."""
    result = list_upcoming_events(prop_id=prop_id, days=days)
    register_action(
        prop_id=prop_id or 0,
        entity_type="housekeeping_events",
        entity_id="upcoming",
        action="read",
        summary=f"Consulta de eventos próximos ({days} días)",
        changed_by=current_user.get("username", "system"),
        metadata={"prop_id": prop_id, "days": days, "url": str(request.url)},
    )
    return result
