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
    complete_housekeeping_task,
    complete_maintenance_task,
    create_additional_charge,
    create_housekeeping_task,
    create_maintenance_task,
    get_housekeeping_dashboard,
    get_room_status,
    list_additional_charges,
    list_housekeeping_tasks,
    list_maintenance_tasks,
    list_room_status,
    module_status,
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
# Dashboard
# ═══════════════════════════════════════════════


@api_router.get("/dashboard")
def housekeeping_dashboard_api(
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_login),
):
    """Return aggregated KPIs for housekeeping efficiency monitoring (CU-E09)."""
    return get_housekeeping_dashboard(prop_id=prop_id)
