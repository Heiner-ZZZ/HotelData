from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from src.app.modules.lost_and_found.schemas import LostItemCreate, LostItemUpdate, ModuleStatus
from src.app.modules.lost_and_found.service import (
    claim_lost_item,
    create_lost_item,
    delete_lost_item,
    dispose_lost_item,
    get_lost_item,
    list_lost_items,
    module_status,
    update_lost_item,
)
from src.app.security.dependencies import require_any_prop_permission
from src.database.connection import get_database

router = APIRouter(prefix="/modules/lost-and-found", tags=["modules-lost-and-found"])
api_router = APIRouter(prefix="/api/lost-and-found", tags=["lost-and-found-api"])


@router.get("/status", response_model=ModuleStatus)
def lost_and_found_module_status() -> ModuleStatus:
    return module_status()


def _require_item_same_hotel(db, item_id: str, prop_id: int | None) -> None:
    """404 (no 403) si el item pertenece a otro hotel — deny cross-hotel."""
    from bson import ObjectId
    from bson.errors import InvalidId
    try:
        query = {"_id": ObjectId(item_id)}
    except InvalidId:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item no encontrado")
    doc = db.lost_and_found.find_one(query, {"prop_id": 1})
    if doc is None or doc.get("prop_id") != prop_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item no encontrado")


def _check_body_prop_id(query_prop_id: int | None, payload) -> None:
    """Consistencia gate(query) ↔ body: el prop_id del query es autoritativo."""
    try:
        body_prop_id = int(str(payload.prop_id or 0))
    except (AttributeError, TypeError, ValueError):
        body_prop_id = 0
    if query_prop_id is not None and body_prop_id != query_prop_id:
        raise HTTPException(status_code=400, detail="prop_id del query y del body no coinciden")


@api_router.post("", status_code=status.HTTP_201_CREATED)
def create_lost_item_api(
    payload: LostItemCreate = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_any_prop_permission("lost-found.create", "housekeeping.create")),
):
    """Register a new lost & found item."""
    _check_body_prop_id(query_prop_id, payload)
    result = create_lost_item(payload)
    # Push SSE event for staff in the same property
    _push_lost_found_event(
        payload.prop_id, "lost_found_create",
        item_name=payload.item_name,
        status="found",
        staff=current_user.get("display_name") or current_user.get("username", "Staff"),
    )
    return result


@api_router.get("")
def list_lost_items_api(
    prop_id: int | None = Query(default=None, ge=1),
    status: str | None = Query(default=None),
    booking_id: str | None = Query(default=None),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_any_prop_permission("lost-found.read", "housekeeping.read")),
):
    """List lost & found items with optional filters."""
    return list_lost_items(
        prop_id=prop_id,
        status_filter=status,
        booking_id=booking_id,
        search=search,
        page=page,
        page_size=page_size,
    )


@api_router.get("/{item_id}")
def get_lost_item_api(
    item_id: str,
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_any_prop_permission("lost-found.read", "housekeeping.read")),
):
    """Get a single lost & found item."""
    _require_item_same_hotel(get_database(), item_id, query_prop_id)
    result = get_lost_item(item_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item no encontrado")
    return result


@api_router.put("/{item_id}")
def update_lost_item_api(
    item_id: str,
    payload: LostItemUpdate = Body(...),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_any_prop_permission("lost-found.update", "housekeeping.update")),
):
    """Update a lost & found item."""
    _require_item_same_hotel(get_database(), item_id, query_prop_id)
    result = update_lost_item(item_id, payload)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item no encontrado")
    return result


@api_router.delete("/{item_id}")
def delete_lost_item_api(
    item_id: str,
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_any_prop_permission("lost-found.delete", "housekeeping.delete")),
):
    """Permanently delete a lost & found item."""
    _require_item_same_hotel(get_database(), item_id, query_prop_id)
    result = delete_lost_item(item_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item no encontrado")
    return result


@api_router.post("/{item_id}/claim")
def claim_lost_item_api(
    item_id: str,
    payload: dict = Body(default={}),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_any_prop_permission("lost-found.update", "housekeeping.update")),
):
    """Mark a lost item as returned to the guest."""
    _require_item_same_hotel(get_database(), item_id, query_prop_id)
    result = claim_lost_item(
        item_id,
        returned_to=str(payload.get("returned_to", "")),
        notes=str(payload.get("notes", "")),
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item no encontrado")
    # Push SSE event
    _push_lost_found_event(
        result.get("prop_id", 0), "lost_found_claim",
        item_name=result.get("item_name", ""),
        status="claimed",
        staff=current_user.get("display_name") or current_user.get("username", "Staff"),
    )
    return result


@api_router.post("/{item_id}/dispose")
def dispose_lost_item_api(
    item_id: str,
    payload: dict = Body(default={}),
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    current_user: dict = Depends(require_any_prop_permission("lost-found.update", "housekeeping.update")),
):
    """Mark a lost item as disposed (donated, thrown away, etc.)."""
    _require_item_same_hotel(get_database(), item_id, query_prop_id)
    result = dispose_lost_item(
        item_id,
        notes=str(payload.get("notes", "")),
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item no encontrado")
    # Push SSE event
    _push_lost_found_event(
        result.get("prop_id", 0), "lost_found_dispose",
        item_name=result.get("item_name", ""),
        status="disposed",
        staff=current_user.get("display_name") or current_user.get("username", "Staff"),
    )
    return result


# ═══════════════════════════════════════════════════════════
# SSE helper
# ═══════════════════════════════════════════════════════════

def _push_lost_found_event(prop_id: int, event_type: str, **kwargs) -> None:
    """Publish a Lost & Found event to the SSE event manager for staff."""
    try:
        from src.app.modules.instay.routes_impl._event_manager import StayEventManager
        StayEventManager.instance_sync().publish_threadsafe(prop_id, event_type, kwargs)
    except Exception:
        pass
