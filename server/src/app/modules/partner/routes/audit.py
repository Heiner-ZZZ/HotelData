"""Audit log endpoint for the partner management section.

Provides a unified view of all auditable actions across room types,
inventory, rates, policies, amenities, and content.
"""

from __future__ import annotations

from fastapi import Depends, Query

from src.app.modules.partner.routes import api_router
from src.app.modules.partner.services.audit import list_audit_entries, get_audit_stats
from src.app.security.dependencies import require_permission

ENTITY_TYPES = [
    "room_type", "inventory_entry", "rate_plan", "rate_calendar",
    "policy", "amenity", "content", "reservation", "housekeeping_task",
    # Traza de acceso a datos sensibles: consulta de la atribución de turno
    # (turno + cajero responsable) de un check-out o folio.
    "shift_attribution_access",
]
ACTIONS = ["create", "update", "delete", "soft_delete", "restore", "batch_update",
           "confirm", "reject", "cancel", "check_in", "check_out", "reassign_room",
           "document_change", "read"]


@api_router.get("/audit-log")
def audit_log_api(
    prop_id: int | None = Query(default=None, ge=1),
    entity_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
    changed_by: str | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=30, ge=1, le=200),
    current_user: dict = Depends(require_permission("audit.read")),
):
    """Return paginated, filtered audit log entries, newest first."""
    return list_audit_entries(
        prop_id=prop_id,
        entity_type=entity_type,
        action=action,
        changed_by=changed_by,
        from_date=from_date,
        to_date=to_date,
        page=page,
        per_page=per_page,
    )


@api_router.get("/audit-log/stats")
def audit_log_stats_api(
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_permission("audit.read")),
):
    """Return aggregate statistics for the audit log."""
    return get_audit_stats(prop_id=prop_id)


@api_router.get("/audit-log/entity-types")
def audit_log_entity_types_api(
    current_user: dict = Depends(require_permission("audit.read")),
):
    """Return the list of tracked entity types for filter dropdowns."""
    return {"entity_types": ENTITY_TYPES, "actions": ACTIONS}
