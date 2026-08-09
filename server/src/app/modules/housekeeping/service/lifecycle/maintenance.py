"""Maintenance task operations."""

from __future__ import annotations

import logging
from math import ceil
from typing import Any

from bson import ObjectId

from pymongo import ReturnDocument

from src.database.connection import get_database
from ..collections import MAINTENANCE_COLLECTION
from ...schemas import MaintenanceTaskCreate, now_iso

logger = logging.getLogger(__name__)


def _resolve_room_from_id(room_id: str, prop_id: int | None = None) -> dict[str, Any] | None:
    """Resolve a hotel room document by its business ID (hotel_room_id).

    Returns the full document including ``_id`` (ObjectId FK) and
    ``hotel_room_id`` (string business key).
    """
    db = get_database()
    query: dict[str, Any] = {"hotel_room_id": room_id}
    if prop_id is not None:
        query["prop_id"] = prop_id
    return db.hotel_rooms.find_one(
        query,
        {"_id": 1, "hotel_room_id": 1, "room_label": 1, "room_type_id": 1, "prop_id": 1, "floor": 1},
    )


def _room_match(prop_id: int, room_id: str | None = None, room_label: str | None = None) -> dict:
    """Build a query that matches a room_status_log doc by hotel_room_id or room_label/room_number."""
    query: dict[str, Any] = {"prop_id": prop_id}
    if room_id:
        query["hotel_room_id"] = room_id
    elif room_label:
        query["$or"] = [{"room_label": room_label}]
    return query


def _sync_expense_invoice_link(
    db: Any,
    *,
    invoice_id: ObjectId,
    task_id: str,
    prop_id: int,
    attach: bool,
) -> None:
    """Maintain a non-stale, same-hotel reverse link for maintenance tasks.

    Older documents used singular ``maintenance_task_id``. The canonical
    representation is the list because one vendor invoice can cover multiple
    work orders. The singular field remains as a compatibility alias pointing
    to the first linked task.
    """
    invoice = db.expense_invoices.find_one({"_id": invoice_id, "prop_id": prop_id})
    if not invoice:
        return
    linked = list(invoice.get("maintenance_task_ids") or [])
    legacy = invoice.get("maintenance_task_id")
    if legacy and legacy not in linked:
        linked.append(str(legacy))
    task_id = str(task_id)
    if attach and task_id not in linked:
        linked.append(task_id)
    if not attach:
        linked = [value for value in linked if str(value) != task_id]
    update: dict[str, Any] = {
        "maintenance_task_ids": linked,
        "updated_at": now_iso(),
    }
    if linked:
        update["maintenance_task_id"] = linked[0]
    else:
        update["maintenance_task_id"] = None
    db.expense_invoices.update_one({"_id": invoice_id, "prop_id": prop_id}, {"$set": update})


def _auto_block_room(db: Any, prop_id: int, room_id: str, room_label: str, scheduled_date: str) -> None:
    """Mark the room as 'maintenance' in room_status_log and create blackout_date.

    RF-002: Bloquear disponibilidad durante mantenimiento.
    This ensures the room cannot be booked while under maintenance.
    """
    if not room_id and not room_label:
        return
    # Route the state change through the canonical transition writer instead
    # of forcing maintenance_requested over an incompatible current state.
    from src.app.modules.housekeeping.schemas import RoomStatusLogCreate
    from src.app.modules.housekeeping.service.lifecycle.status import upsert_room_status
    room = db.hotel_rooms.find_one(
        {"prop_id": prop_id, "hotel_room_id": room_id},
        {"room_type_id": 1},
    )
    upsert_room_status(RoomStatusLogCreate(
        prop_id=prop_id,
        room_type_id=(room or {}).get("room_type_id", ""),
        room_label=room_label,
        status="maintenance_requested",
        note="Mantenimiento programado",
    ))
    # Create blackout date entry for the scheduled date
    if scheduled_date:
        existing = db.blackout_dates.find_one({
            "prop_id": prop_id,
            "hotel_room_id": room_id,
            "start_date": scheduled_date,
            "end_date": scheduled_date,
            "source": "maintenance",
        })
        if not existing:
            db.blackout_dates.insert_one({
                "prop_id": prop_id,
                "room_label": room_label,
                "hotel_room_id": room_id,
                "start_date": scheduled_date,
                "end_date": scheduled_date,
                "source": "maintenance",
                "reason": "Mantenimiento programado",
                "created_at": now_iso(),
            })


def _unblock_room(db: Any, prop_id: int, room_id: str, room_label: str, scheduled_date: str) -> None:
    """Restore room status to 'available' and remove blackout dates.

    Called when maintenance is completed or deleted.
    """
    if not room_id and not room_label:
        return
    # Only restore if the room is still in a blocked state — prefer hotel_room_id
    match = _room_match(prop_id, room_id=room_id, room_label=room_label)
    current = db.room_status_log.find_one(match, {"status": 1})
    if current and current.get("status") in ("maintenance_requested", "out_of_service", "out_of_order"):
        # Restore to vacant_clean (the new housekeeping status)
        from src.app.modules.housekeeping.schemas import RoomStatusLogCreate
        from src.app.modules.housekeeping.service.lifecycle.status import upsert_room_status
        room = db.hotel_rooms.find_one(
            {"prop_id": prop_id, "hotel_room_id": room_id},
            {"room_type_id": 1},
        )
        try:
            upsert_room_status(RoomStatusLogCreate(
                prop_id=prop_id,
                room_type_id=(room or {}).get("room_type_id", ""),
                room_label=room_label,
                status="vacant_clean",
                note="",
            ))
        except ValueError:
            logger.warning(
                "Room %s changed while maintenance was active; leaving current status intact",
                room_id or room_label,
            )
    # Remove blackout dates created by maintenance
    if scheduled_date:
        db.blackout_dates.delete_many({
            "prop_id": prop_id,
            "$or": [
                {"hotel_room_id": room_id},
                {"room_label": room_label},
            ],
            "start_date": scheduled_date,
            "end_date": scheduled_date,
            "source": "maintenance",
        })


def reconcile_no_cost_maintenance(
    task_id: str,
    *,
    changed_by: str = "historical_reconciliation",
) -> dict[str, Any] | None:
    """Classify a maintenance task with no recorded financial impact.

    This does not invent a vendor, invoice, journal, or cost. It makes the
    absence explicit (`actual_cost=0`, `no_cost_recorded`) and stores one
    immutable reconciliation record so operational and reporting projections
    converge on retries.
    """
    db = get_database()
    try:
        task_oid = ObjectId(task_id)
    except Exception:
        return None
    task = db[MAINTENANCE_COLLECTION].find_one({"_id": task_oid, "status": {"$ne": "deleted"}})
    if not task:
        return None
    if (
        float(task.get("actual_cost") or 0) > 0
        or task.get("expense_invoice_id")
        or task.get("vendor_id")
        or task.get("vendor_name")
        or task.get("ledger_journal_id")
        or float(task.get("estimated_cost") or 0) > 0
    ):
        return None

    now = now_iso()
    reconciliation = {
        "action": "classified_no_cost_recorded",
        "reason": "no_actual_cost_vendor_invoice_or_ledger_evidence",
        "changed_by": changed_by,
        "changed_at": now,
    }
    db[MAINTENANCE_COLLECTION].update_one(
        {"_id": task_oid},
        {"$set": {
            "actual_cost": 0.0,
            "financial_link_status": "no_cost_recorded",
            "financial_link_error": None,
            "ledger_status": "not_applicable",
            "ledger_posting_status": "not_applicable",
            "ledger_posting_error": None,
            "metadata.reconciliation": reconciliation,
            "updated_at": now,
        }},
    )
    db.maintenance_financial_reconciliations.update_one(
        {"task_id": str(task_oid)},
        {"$setOnInsert": {
            "task_id": str(task_oid),
            "prop_id": task.get("prop_id", 0),
            "action": "classified_no_cost_recorded",
            "reason": reconciliation["reason"],
            "changed_by": changed_by,
            "changed_at": now,
        }},
        upsert=True,
    )
    refreshed = db[MAINTENANCE_COLLECTION].find_one({"_id": task_oid})
    if refreshed:
        try:
            from src.app.modules.financial_reconciliation.domain_events import append_domain_event
            append_domain_event(
                prop_id=int(refreshed.get("prop_id", 0) or 0),
                event_type="operations.maintenance.no_cost_recorded",
                aggregate_type="operations",
                aggregate_id=str(task_oid),
                idempotency_key=f"live:maintenance:no-cost:{task_oid}",
                payload={"actual_cost": 0.0, "financial_link_status": "no_cost_recorded"},
                source_collection=MAINTENANCE_COLLECTION,
                source_id=str(task_oid),
                actor_id=changed_by,
            )
        except Exception:
            logger.exception("Failed to emit maintenance reconciliation event %s", task_oid)
    return _enrich_mt_task(refreshed) if refreshed else None


def create_maintenance_task(payload: MaintenanceTaskCreate) -> dict[str, Any]:
    db = get_database()
    now = now_iso()
    room = _resolve_room_from_id(payload.room_id, payload.prop_id)
    if not room:
        raise ValueError(f"Habitación no encontrada: {payload.room_id}")

    status = payload.status or "scheduled"
    completed_at = now if status == "completed" else None
    room_label = room.get("room_label") or payload.room_id
    doc = {
        "prop_id": room["prop_id"],
        "room_id": room["_id"],
        "hotel_room_id": room["hotel_room_id"],
        "room_label": room_label,
        "room_type_id": room.get("room_type_id", ""),
        "task_type": payload.task_type,
        "title": payload.title,
        "description": payload.description,
        "status": status,
        "priority": payload.priority,
        "scheduled_date": payload.scheduled_date,
        "auto_block": payload.auto_block,
        "estimated_cost": payload.estimated_cost,
        "actual_cost": payload.actual_cost,
        "currency": payload.currency,
        "vendor_name": payload.vendor_name,
        "vendor_id": payload.vendor_id,
        "expense_invoice_id": payload.expense_invoice_id,
        "ledger_journal_id": payload.ledger_journal_id,
        "inventory_consumption_ids": payload.inventory_consumption_ids,
        "created_at": now,
        "completed_at": completed_at,
    }
    result = db[MAINTENANCE_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id

    # Link the maintenance work order to the vendor bill without creating or
    # paying a bill implicitly. The expense invoice remains the AP source of
    # truth; this only validates same-hotel ownership and records a stable
    # reverse link for reconciliation.
    if payload.expense_invoice_id:
        try:
            invoice_id = ObjectId(payload.expense_invoice_id)
        except Exception as exc:
            db[MAINTENANCE_COLLECTION].update_one(
                {"_id": result.inserted_id},
                {"$set": {"financial_link_status": "invalid_invoice", "financial_link_error": str(exc)}},
            )
        else:
            invoice = db.expense_invoices.find_one({"_id": invoice_id, "prop_id": room["prop_id"]}, {"_id": 1})
            if invoice:
                db[MAINTENANCE_COLLECTION].update_one(
                    {"_id": result.inserted_id},
                    {"$set": {
                        "expense_invoice_id": str(invoice_id),
                        "ledger_status": "pending",
                        "financial_link_status": "linked",
                        "financial_link_error": None,
                    }},
                )
                _sync_expense_invoice_link(
                    db,
                    invoice_id=invoice_id,
                    task_id=str(result.inserted_id),
                    prop_id=room["prop_id"],
                    attach=True,
                )
            else:
                db[MAINTENANCE_COLLECTION].update_one(
                    {"_id": result.inserted_id},
                    {"$set": {"financial_link_status": "invoice_not_found_or_foreign", "financial_link_error": "La factura no pertenece al hotel"}},
                )
    # RF-002: Auto-block room availability if auto_block is True and not completed
    if payload.auto_block and status != "completed":
        try:
            _auto_block_room(db, room["prop_id"], room["hotel_room_id"], room_label, payload.scheduled_date)
        except Exception:
            logger.exception("Failed to auto-block room for maintenance task")
    # Reload after financial linking so the response cannot claim ``not_linked``
    # while Mongo already contains the vendor invoice relationship.
    persisted = db[MAINTENANCE_COLLECTION].find_one({"_id": result.inserted_id}) or doc
    try:
        from src.app.modules.financial_reconciliation.domain_events import append_domain_event
        append_domain_event(
            prop_id=int(persisted.get("prop_id", 0) or 0),
            event_type=f"operations.maintenance.{status}",
            aggregate_type="operations",
            aggregate_id=str(result.inserted_id),
            idempotency_key=f"live:maintenance:created:{result.inserted_id}",
            payload={"status": status, "actual_cost": persisted.get("actual_cost"), "expense_invoice_id": persisted.get("expense_invoice_id")},
            source_collection=MAINTENANCE_COLLECTION,
            source_id=str(result.inserted_id),
        )
    except Exception:
        logger.exception("Failed to emit maintenance event %s", result.inserted_id)
    return _enrich_mt_task(persisted)


def list_maintenance_tasks(
    prop_id: int | None = None, status_filter: str | None = None,
    priority: str | None = None,
    page: int = 1, page_size: int = 20,
) -> dict[str, Any]:
    db = get_database()
    query: dict[str, Any] = {"status": {"$ne": "deleted"}}
    if prop_id:
        query["prop_id"] = prop_id
    if status_filter:
        query["status"] = status_filter
    if priority:
        query["priority"] = priority
    total = db[MAINTENANCE_COLLECTION].count_documents(query)
    cursor = db[MAINTENANCE_COLLECTION].find(query).sort("scheduled_date", -1).skip((page - 1) * page_size).limit(page_size)
    items = [_enrich_mt_task(doc) for doc in cursor]
    return {
        "items": items, "total": total, "page": page, "page_size": page_size,
        "total_pages": max(1, ceil(total / page_size)),
        "has_next": page * page_size < total, "has_prev": page > 1,
    }


def update_maintenance_task(task_id: str, payload: MaintenanceTaskCreate) -> dict[str, Any] | None:
    db = get_database()
    now = now_iso()
    status = payload.status or "scheduled"
    # Resolve room from the provided room_id so denormalized fields stay in sync
    room = _resolve_room_from_id(payload.room_id, payload.prop_id)
    if not room:
        raise ValueError(f"Habitación no encontrada: {payload.room_id}")

    # Fetch previous state to know if we need to unblock old room
    prev = db[MAINTENANCE_COLLECTION].find_one({"_id": ObjectId(task_id)})
    room_label = room.get("room_label") or payload.room_id

    set_data = {
        "prop_id": room["prop_id"],
        "room_id": room["_id"],
        "hotel_room_id": room["hotel_room_id"],
        "room_label": room_label,
        "room_type_id": room.get("room_type_id", ""),
        "task_type": payload.task_type,
        "title": payload.title,
        "description": payload.description or "",
        "priority": payload.priority,
        "scheduled_date": payload.scheduled_date,
        "auto_block": payload.auto_block,
        "estimated_cost": payload.estimated_cost,
        "actual_cost": payload.actual_cost,
        "currency": payload.currency,
        "vendor_name": payload.vendor_name,
        "vendor_id": payload.vendor_id,
        "expense_invoice_id": payload.expense_invoice_id,
        "ledger_journal_id": payload.ledger_journal_id,
        "inventory_consumption_ids": payload.inventory_consumption_ids,
        "status": status,
        "updated_at": now,
    }
    if status == "completed":
        set_data["completed_at"] = now
    else:
        set_data["completed_at"] = None

    if payload.expense_invoice_id:
        try:
            invoice_id = ObjectId(payload.expense_invoice_id)
        except Exception as exc:
            raise ValueError(f"Factura de proveedor inválida: {exc}") from exc
        invoice = db.expense_invoices.find_one({"_id": invoice_id, "prop_id": room["prop_id"]}, {"_id": 1})
        if not invoice:
            raise ValueError("La factura de proveedor no existe o pertenece a otro hotel")
        set_data["expense_invoice_id"] = str(invoice_id)
        set_data["ledger_status"] = prev.get("ledger_status", "pending") if prev else "pending"
        set_data["financial_link_status"] = "linked"
        set_data["financial_link_error"] = None

    doc = db[MAINTENANCE_COLLECTION].find_one_and_update(
        {"_id": ObjectId(task_id)},
        {"$set": set_data},
        return_document=ReturnDocument.AFTER,
    )
    if doc:
        previous_invoice_id = prev.get("expense_invoice_id") if prev else None
        next_invoice_id = payload.expense_invoice_id
        if previous_invoice_id and previous_invoice_id != next_invoice_id:
            try:
                _sync_expense_invoice_link(
                    db,
                    invoice_id=ObjectId(str(previous_invoice_id)),
                    task_id=task_id,
                    prop_id=int(prev.get("prop_id", room["prop_id"])),
                    attach=False,
                )
            except Exception:
                logger.exception("Failed to detach maintenance %s from prior expense invoice", task_id)
        if next_invoice_id:
            _sync_expense_invoice_link(
                db,
                invoice_id=ObjectId(str(next_invoice_id)),
                task_id=task_id,
                prop_id=room["prop_id"],
                attach=True,
            )
        else:
            db[MAINTENANCE_COLLECTION].update_one(
                {"_id": ObjectId(task_id)},
                {"$set": {
                    "ledger_status": "not_linked",
                    "ledger_journal_id": None,
                    "financial_link_status": "not_linked",
                    "financial_link_error": None,
                }},
            )
    if doc:
        # If auto_block was enabled on prev, unblock old first
        if prev and prev.get("auto_block"):
            _unblock_room(
                db,
                prev.get("prop_id", 0),
                prev.get("hotel_room_id", "") or str(prev.get("room_id", "")),
                prev.get("room_label", ""),
                prev.get("scheduled_date", ""),
            )

        # If new status is not completed and auto_block is True, block new room/date
        if status != "completed" and payload.auto_block:
            _auto_block_room(
                db,
                room["prop_id"],
                room["hotel_room_id"],
                room_label,
                payload.scheduled_date,
            )

    return _enrich_mt_task(doc) if doc else None


def complete_maintenance_task(task_id: str, note: str = "") -> dict[str, Any] | None:
    db = get_database()
    now = now_iso()
    update = {"$set": {"status": "completed", "completed_at": now}}
    if note:
        update["$set"]["note"] = note
    doc = db[MAINTENANCE_COLLECTION].find_one_and_update(
        {"_id": ObjectId(task_id), "status": {"$in": ["scheduled", "in_progress", "inspection"]}},
        update, return_document=True,
    )
    if doc and doc.get("auto_block"):
        try:
            _unblock_room(
                db,
                doc.get("prop_id", 0),
                doc.get("hotel_room_id", "") or str(doc.get("room_id", "")),
                doc.get("room_label", ""),
                doc.get("scheduled_date", ""),
            )
        except Exception:
            logger.exception("Failed to unblock room on maintenance completion")
    return _enrich_mt_task(doc) if doc else None


def delete_maintenance_task(task_id: str) -> dict[str, Any] | None:
    db = get_database()
    now = now_iso()
    previous = db[MAINTENANCE_COLLECTION].find_one({"_id": ObjectId(task_id)})
    doc = db[MAINTENANCE_COLLECTION].find_one_and_update(
        {"_id": ObjectId(task_id), "status": {"$ne": "deleted"}},
        {"$set": {"status": "deleted", "deleted_at": now}},
        return_document=True,
    )
    if doc and previous and previous.get("expense_invoice_id"):
        try:
            _sync_expense_invoice_link(
                db,
                invoice_id=ObjectId(str(previous["expense_invoice_id"])),
                task_id=task_id,
                prop_id=int(previous.get("prop_id", 0) or 0),
                attach=False,
            )
        except Exception:
            logger.exception("Failed to detach deleted maintenance %s from expense invoice", task_id)
    if doc and doc.get("auto_block"):
        try:
            _unblock_room(
                db,
                doc.get("prop_id", 0),
                doc.get("hotel_room_id", "") or str(doc.get("room_id", "")),
                doc.get("room_label", ""),
                doc.get("scheduled_date", ""),
            )
        except Exception:
            logger.exception("Failed to unblock room on maintenance deletion")
    return _enrich_mt_task(doc) if doc else None


def _enrich_mt_task(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    # camelCase aliases for frontend
    doc["propId"] = doc.get("prop_id", 0)
    # ``roomId`` is the stable business key consumed by the API/UI; retain
    # the Mongo ObjectId separately as ``room_object_id`` for diagnostics.
    if doc.get("room_id") is not None and not doc.get("hotel_room_id"):
        doc["room_object_id"] = str(doc["room_id"])
    doc["roomId"] = doc.get("hotel_room_id") or doc.get("room_id", "")
    doc["roomLabel"] = doc.get("room_label", "")
    doc["roomTypeId"] = doc.get("room_type_id", "")
    doc["roomNumber"] = doc.get("room_number") or doc.get("room_label", "")
    doc["taskType"] = doc.get("task_type", "")
    doc["scheduledDate"] = doc.get("scheduled_date", "")
    doc["autoBlock"] = doc.get("auto_block", False)
    doc["estimatedCost"] = doc.get("estimated_cost")
    doc["actualCost"] = doc.get("actual_cost")
    doc["currency"] = doc.get("currency", "USD")
    doc["vendorName"] = doc.get("vendor_name")
    doc["vendorId"] = doc.get("vendor_id")
    doc["inventoryConsumptionIds"] = list(doc.get("inventory_consumption_ids") or [])
    doc["expenseInvoiceId"] = doc.get("expense_invoice_id")
    doc["ledgerJournalId"] = doc.get("ledger_journal_id")
    doc["ledgerStatus"] = doc.get("ledger_status", "pending" if doc.get("expense_invoice_id") else "not_linked")
    doc["ledgerPostingStatus"] = doc.get("ledger_posting_status")
    doc["ledgerPostingError"] = doc.get("ledger_posting_error")
    doc["financialLinkStatus"] = doc.get("financial_link_status", "not_linked")
    doc["financialLinkError"] = doc.get("financial_link_error")
    doc["costStatus"] = doc.get("cost_status") or doc.get("financial_link_status")
    for f in ("created_at", "completed_at"):
        if f in doc:
            doc[f] = _fmt(doc[f])
    doc["createdAt"] = doc.get("created_at")
    doc["completedAt"] = doc.get("completed_at")
    return doc


def _fmt(val):
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val) if val else None
