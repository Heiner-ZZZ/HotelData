"""Room status operations and enrichment helpers.

Implements the complete hotel housekeeping cycle with status transitions.
"""

from __future__ import annotations

from math import ceil
from typing import Any

from bson import ObjectId

from src.database.connection import get_database
from ..collections import ROOM_STATUS_COLLECTION
from ...schemas import (
    RoomStatusLogCreate, is_valid_transition, get_valid_next_statuses,
    ROOM_STATUSES, ROOM_STATUS_COLORS, now_iso,
)

HOTEL_ROOMS_COLLECTION = "hotel_rooms"


def list_valid_transitions(status: str | None = None) -> dict:
    """Return valid transitions for the frontend dropdown builder."""
    if status:
        return {"current": status, "valid_next": get_valid_next_statuses(status)}
    return {
        "statuses": ROOM_STATUSES,
        "transitions": {k: v for k, v in {
            s: get_valid_next_statuses(s) for s in ROOM_STATUSES
        }.items() if v},
        "colors": ROOM_STATUS_COLORS,
    }


def _get_current_status(prop_id: int, room_label: str) -> str | None:
    """Fetch the current status of a room from room_status_log."""
    db = get_database()
    existing = db[ROOM_STATUS_COLLECTION].find_one(
        {"prop_id": prop_id, "room_label": room_label},
        {"_id": 0, "status": 1},
    )
    return existing.get("status") if existing else None


def upsert_room_status(payload: RoomStatusLogCreate) -> dict[str, Any]:
    db = get_database()
    now = now_iso()

    # Get old status before updating
    old_status = _get_current_status(payload.prop_id, payload.room_label)

    # ── Validate transition ──
    if old_status is not None and old_status != payload.status:
        if not is_valid_transition(old_status, payload.status):
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                "Invalid status transition for room %s (prop %s): %s → %s",
                payload.room_label, payload.prop_id, old_status, payload.status,
            )
            # Allow the transition anyway with warning (PMS should be flexible)
            # but log it for audit

    # ── Auto-transition: if syncing from hotel_rooms, default to vacant_clean ──

    doc = {
        "prop_id": payload.prop_id, "room_type_id": payload.room_type_id,
        "room_label": payload.room_label, "status": payload.status,
        "note": payload.note, "updated_at": now,
    }
    result = db[ROOM_STATUS_COLLECTION].update_one(
        {"prop_id": payload.prop_id, "room_label": payload.room_label},
        {"$set": doc, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    if result.upserted_id:
        doc["_id"] = result.upserted_id
        doc["created_at"] = now
    else:
        existing = db[ROOM_STATUS_COLLECTION].find_one(
            {"prop_id": payload.prop_id, "room_label": payload.room_label}
        )
        if existing:
            doc["_id"] = existing["_id"]
            doc["created_at"] = existing.get("created_at", now)

    # ── Log history if status changed ──
    if old_status is not None and old_status != payload.status:
        from .room_history import log_room_status_change
        log_room_status_change(
            prop_id=payload.prop_id,
            room_label=payload.room_label,
            old_status=old_status,
            new_status=payload.status,
            note=payload.note or "",
            changed_by="api",
        )
    elif old_status is None:
        # First creation — log as available
        from .room_history import log_room_status_change
        log_room_status_change(
            prop_id=payload.prop_id,
            room_label=payload.room_label,
            old_status="",
            new_status=payload.status,
            note=payload.note or "Inicial",
            changed_by="api",
        )

    return _enrich_room_status(doc)


def list_room_status(
    prop_id: int | None = None,
    status_filter: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    db = get_database()
    query: dict[str, Any] = {}
    if prop_id:
        query["prop_id"] = prop_id
    if status_filter:
        query["status"] = status_filter
    total = db[ROOM_STATUS_COLLECTION].count_documents(query)
    cursor = db[ROOM_STATUS_COLLECTION].find(query).sort("room_label", 1).skip((page - 1) * page_size).limit(page_size)
    items = [_enrich_room_status(doc) for doc in cursor]
    return {
        "items": items, "total": total, "page": page, "page_size": page_size,
        "total_pages": max(1, ceil(total / page_size)),
        "has_next": page * page_size < total, "has_prev": page > 1,
    }


def get_room_status(record_id: str) -> dict[str, Any] | None:
    db = get_database()
    doc = db[ROOM_STATUS_COLLECTION].find_one({"_id": ObjectId(record_id)})
    return _enrich_room_status(doc) if doc else None


def update_room_status_bulk(prop_id: int, room_labels: list[str], new_status: str, note: str = "") -> int:
    db = get_database()
    now = now_iso()

    # Fetch old statuses before bulk update
    old_docs = list(
        db[ROOM_STATUS_COLLECTION].find(
            {"prop_id": prop_id, "room_label": {"$in": room_labels}},
            {"_id": 0, "room_label": 1, "status": 1},
        )
    )
    old_status_map: dict[str, str] = {d["room_label"]: d["status"] for d in old_docs}

    result = db[ROOM_STATUS_COLLECTION].update_many(
        {"prop_id": prop_id, "room_label": {"$in": room_labels}},
        {"$set": {"status": new_status, "note": note, "updated_at": now}},
    )

    # ── Log history for each changed room ──
    from .room_history import log_room_status_change
    for label in room_labels:
        old = old_status_map.get(label)
        if old is not None and old != new_status:
            log_room_status_change(
                prop_id=prop_id,
                room_label=label,
                old_status=old,
                new_status=new_status,
                note=note or "",
                changed_by="api:bulk_update",
            )
        elif old is None:
            log_room_status_change(
                prop_id=prop_id,
                room_label=label,
                old_status="",
                new_status=new_status,
                note=note or "Inicial",
                changed_by="api:bulk_update",
            )

    return result.modified_count


def sync_room_status_from_hotel_rooms(prop_id: int) -> dict[str, Any]:
    """Auto‑seed room_status_log from hotel_rooms for a property.

    Creates missing records (does not overwrite existing ones) so the
    housekeeping rooms page reflects all known rooms.
    Default status is 'vacant_clean'.
    """
    db = get_database()
    now = now_iso()
    rooms = list(db[HOTEL_ROOMS_COLLECTION].find(
        {"prop_id": prop_id},
        {"hotel_room_id": 1, "room_type_id": 1, "room_label": 1, "floor": 1, "is_active": 1},
    ))

    created = 0
    for room in rooms:
        hotel_room_id = room.get("hotel_room_id", "")
        room_type_id = room.get("room_type_id", "")
        room_label = room.get("room_label", "")
        floor = room.get("floor")
        # Auto-derive floor from room_label if missing (e.g. '301' → '3')
        if not floor:
            rn = room.get("room_label", "")
            if rn and rn.isdigit():
                floor = str(int(rn) // 100)
        if not hotel_room_id:
            continue

        existing = db[ROOM_STATUS_COLLECTION].find_one(
            {"prop_id": prop_id, "hotel_room_id": hotel_room_id},
            {"_id": 1, "floor": 1},
        )
        if existing:
            # Update floor if it's missing or changed
            existing_floor = existing.get("floor")
            if (floor is not None) and (existing_floor is None or existing_floor != floor):
                db[ROOM_STATUS_COLLECTION].update_one(
                    {"_id": existing["_id"]},
                    {"$set": {"floor": floor, "updated_at": now}}
                )
            continue

        doc = {
            "prop_id": prop_id,
            "hotel_room_id": hotel_room_id,
            "room_type_id": room_type_id,
            "room_label": room_label,
            "status": "vacant_clean",
            "note": "",
            "created_at": now,
            "updated_at": now,
        }
        if floor is not None:
            doc["floor"] = floor
        db[ROOM_STATUS_COLLECTION].insert_one(doc)
        created += 1

    return {"synced": True, "prop_id": prop_id, "created": created, "total_rooms": len(rooms)}


def cleanup_orphan_room_status(prop_id: int | None = None) -> dict[str, Any]:
    """Remove room_status_log entries whose hotel_room_id no longer exists
    in hotel_rooms, or whose room_type_id no longer exists in room_types.

    This fixes the discrepancy where the housekeeping dashboard shows more
    rooms than the rooms management page due to orphaned status records
    left behind after room type / hotel room deletion.
    """
    db = get_database()

    match: dict[str, Any] = {}
    if prop_id:
        match["prop_id"] = prop_id

    # Build sets of valid IDs
    valid_hotel_room_ids: set[str] = set()
    for doc in db[HOTEL_ROOMS_COLLECTION].find(
        {"prop_id": prop_id} if prop_id else {},
        {"hotel_room_id": 1},
    ):
        if doc.get("hotel_room_id"):
            valid_hotel_room_ids.add(doc["hotel_room_id"])

    valid_room_type_ids: set[str] = set()
    for doc in db.room_types.find(
        {"prop_id": prop_id} if prop_id else {},
        {"room_type_id": 1},
    ):
        if doc.get("room_type_id"):
            valid_room_type_ids.add(doc["room_type_id"])

    # Find orphaned records: hotel_room_id exists but not in hotel_rooms
    orphaned_by_hrid: list[str] = []
    for doc in db[ROOM_STATUS_COLLECTION].find(
        {**match, "hotel_room_id": {"$exists": True, "$ne": ""}},
        {"room_label": 1, "hotel_room_id": 1},
    ):
        hrid = doc.get("hotel_room_id", "")
        if hrid and hrid not in valid_hotel_room_ids:
            orphaned_by_hrid.append(hrid)

    # Find orphaned records: room_type_id exists but not in room_types
    orphaned_by_rtid: list[str] = []
    for doc in db[ROOM_STATUS_COLLECTION].find(
        {**match, "room_type_id": {"$exists": True, "$ne": ""}},
        {"room_label": 1, "room_type_id": 1},
    ):
        rtid = doc.get("room_type_id", "")
        if rtid and rtid not in valid_room_type_ids:
            orphaned_by_rtid.append(rtid)

    # Also find records with no hotel_room_id at all (purely manual creates)
    # that don't match any hotel_rooms room_label
    valid_labels: set[str] = set()
    for doc in db[HOTEL_ROOMS_COLLECTION].find(
        {"prop_id": prop_id} if prop_id else {},
        {"room_label": 1},
    ):
        if doc.get("room_label"):
            valid_labels.add(doc["room_label"])

    orphaned_by_label: list[str] = []
    for doc in db[ROOM_STATUS_COLLECTION].find(
        {**match, "hotel_room_id": {"$in": ["", None]}},
        {"room_label": 1},
    ):
        label = doc.get("room_label", "")
        if label and label not in valid_labels:
            orphaned_by_label.append(label)

    # Build combined deletion query
    delete_query: dict[str, Any] = {**match}
    or_conditions: list[dict[str, Any]] = []
    if orphaned_by_hrid:
        or_conditions.append({"hotel_room_id": {"$in": orphaned_by_hrid}})
    if orphaned_by_rtid:
        or_conditions.append({"room_type_id": {"$in": orphaned_by_rtid}})
    if orphaned_by_label:
        or_conditions.append({
            "hotel_room_id": {"$in": ["", None]},
            "room_label": {"$in": orphaned_by_label},
        })

    deleted = 0
    if or_conditions:
        delete_query["$or"] = or_conditions
        result = db[ROOM_STATUS_COLLECTION].delete_many(delete_query)
        deleted = result.deleted_count

    return {
        "prop_id": prop_id,
        "deleted": deleted,
        "orphaned_summary": {
            "by_hotel_room_id": len(orphaned_by_hrid),
            "by_room_type_id": len(orphaned_by_rtid),
            "by_label_no_hrid": len(orphaned_by_label),
        },
        "valid_counts": {
            "hotel_rooms": len(valid_hotel_room_ids),
            "room_types": len(valid_room_type_ids),
            "valid_labels": len(valid_labels),
        },
    }

def get_room_status_analytics(
    prop_id: int | None = None,
    status_filter: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    """Dashboard simple O1.2: matriz de estado de habitaciones (Mongo).

    Lee ``room_status_log`` directamente. Devuelve resumen (totales por grupo:
    ocupadas, vacantes, limpieza, mantenimiento, fuera de servicio + tasa de
    ocupación), distribución por estado para el gráfico central del patrón Z
    y una grilla paginada de habitaciones con su estado actual.

    El ``summary``/``distribution`` se calculan SIEMPRE sobre toda la propiedad
    (panorama global); el filtro ``status_filter`` + ``page`` solo afecta a la
    grilla ``rows``, coherente con el patrón Z de los dashboards simples.
    """
    db = get_database()
    query: dict[str, Any] = {}
    if prop_id:
        query["prop_id"] = prop_id

    pipeline = [{"$match": query}, {"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    raw_counts = {r["_id"]: r["count"] for r in db[ROOM_STATUS_COLLECTION].aggregate(pipeline)}

    # Normaliza todos los estados conocidos a 0
    status_counts: dict[str, int] = {s: 0 for s in ROOM_STATUSES}
    status_counts.update(raw_counts)
    total = sum(status_counts.values())

    occupied = status_counts.get("occupied_clean", 0) + status_counts.get("occupied_dirty", 0)
    vacant = status_counts.get("vacant_clean", 0) + status_counts.get("vacant_dirty", 0)
    cleaning = status_counts.get("cleaning_in_progress", 0) + status_counts.get("cleaning_completed", 0)
    maintenance = status_counts.get("maintenance_requested", 0)
    out_of_service = status_counts.get("out_of_service", 0) + status_counts.get("out_of_order", 0)
    inspected = status_counts.get("inspected", 0)
    pending_dirty = status_counts.get("vacant_dirty", 0) + status_counts.get("occupied_dirty", 0)
    clean_ready = status_counts.get("vacant_clean", 0) + status_counts.get("inspected", 0)

    # Distribución para el gráfico (solo estados con > 0)
    distribution = [
        {
            "status": s,
            "label": ROOM_STATUSES.get(s, s),
            "count": c,
            "color": ROOM_STATUS_COLORS.get(s, "#6f797d"),
        }
        for s, c in status_counts.items()
        if c > 0
    ]
    distribution.sort(key=lambda item: item["count"], reverse=True)

    # Grilla paginada + filtro de estado (solo afecta a rows, no al summary)
    rows_query: dict[str, Any] = dict(query)
    if status_filter:
        rows_query["status"] = status_filter
    rows_total = db[ROOM_STATUS_COLLECTION].count_documents(rows_query)
    rows_cursor = (
        db[ROOM_STATUS_COLLECTION]
        .find(rows_query)
        .sort("room_label", 1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    rows = [_enrich_room_status(doc) for doc in rows_cursor]

    return {
        "available": True,
        "source": "mongodb",
        "prop_id": prop_id,
        "summary": {
            "total": total,
            "occupied": occupied,
            "vacant": vacant,
            "cleaning": cleaning,
            "inspected": inspected,
            "maintenance": maintenance,
            "out_of_service": out_of_service,
            "pending_dirty": pending_dirty,
            "clean_ready": clean_ready,
            "occupancy_rate": round((occupied / total) * 100, 1) if total else 0.0,
        },
        "distribution": distribution,
        "status_counts": status_counts,
        "status_labels": ROOM_STATUSES,
        "status_colors": ROOM_STATUS_COLORS,
        "rows": rows,
        "total": rows_total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, ceil(rows_total / page_size)) if rows_total else 1,
        "has_next": page * page_size < rows_total,
        "has_prev": page > 1,
    }


def _fmt(val):
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val) if val else None


def _enrich_room_status(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    for f in ("created_at", "updated_at"):
        if f in doc:
            doc[f] = _fmt(doc[f])
    # camelCase aliases for frontend
    doc["roomLabel"] = doc.get("room_label", "")
    doc["roomNumber"] = doc.get("room_label", "")
    doc["roomTypeId"] = doc.get("room_type_id", "")
    doc["propId"] = doc.get("prop_id", 0)
    doc["hotelRoomId"] = doc.get("hotel_room_id", "")
    doc["floor"] = doc.get("floor")
    return doc
