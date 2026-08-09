"""Hotel products: billable items/perks that can be added to bookings.

Each hotel can define products (e.g. "Cama extra", "Desayuno", "Parking")
with a unit price and available quantity. These products can be added
to active reservations as line items during the guest's stay.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

from src.app.core.resolvers import resolve_hotel_id
from src.app.modules.partner.services._common import clean_text, now_utc
from src.app.modules.partner.services.audit import register_action
from src.database.connection import get_database

logger = logging.getLogger(__name__)


def list_hotel_products(prop_id: int) -> list[dict[str, Any]]:
    """List all billable products for a hotel.

    Each product is enriched with ``last_purchase_invoice`` — the resolved
    expense invoice (id, vendor_name, invoice_date, total, status) when
    ``last_purchase_invoice_ref`` is a real invoice FK, or ``None`` for
    legacy free-text refs / dangling ids. The raw ref field is left intact.

    The enrichment runs as ONE batched ``find`` over the valid ObjectId refs
    (``$in`` + ``prop_id``) instead of an N+1 of per-product ``find_one``
    calls. Legacy free-text refs (e.g. ``INV-001``) are skipped in Python —
    the same way ``ObjectId()`` rejects them — so they resolve to ``None``
    without ever hitting the invoices collection.
    """
    db = get_database()
    items = list(
        db.hotel_products.find({"prop_id": prop_id}, {"_id": 0})
        .sort([("category", 1), ("name", 1)])
    )
    for item in items:
        item.setdefault("unit_price", 0.0)
        item.setdefault("quantity_available", 0)
        item.setdefault("is_active", True)
        item["last_purchase_invoice"] = None  # default; enriched below

    # Collect the ObjectId refs to resolve in one round trip.
    ref_to_oids: dict[str, ObjectId] = {}
    for item in items:
        ref = item.get("last_purchase_invoice_ref")
        if not ref:
            continue
        try:
            oid = ObjectId(ref)
        except (InvalidId, TypeError):
            # Legacy free-text ref ("INV-001") or a corrupt non-string value →
            # stays None. ``if not ref`` above already excluded None/empty;
            # TypeError covers unexpected non-string truthy data.
            continue
        ref_to_oids[ref] = oid
    if not ref_to_oids:
        return items

    invoices = {
        str(doc["_id"]): doc
        for doc in db.expense_invoices.find(
            {"_id": {"$in": list(ref_to_oids.values())}, "prop_id": prop_id},
            {"vendor_name": 1, "invoice_date": 1, "due_date": 1, "total": 1, "status": 1},
        )
    }
    for item in items:
        oid = ref_to_oids.get(item.get("last_purchase_invoice_ref"))
        if oid is None:
            continue
        inv = invoices.get(str(oid))
        if not inv:
            continue  # dangling id / cross-prop → stays None
        item["last_purchase_invoice"] = {
            "id": str(oid),
            "vendor_name": inv.get("vendor_name") or "",
            "invoice_date": inv.get("invoice_date") or "",
            "due_date": inv.get("due_date") or "",
            "total": round(float(inv.get("total") or 0.0), 2),
            "status": inv.get("status") or "",
        }
    return items


def create_hotel_product(
    prop_id: int,
    *,
    name: str,
    description: str = "",
    unit_price: float = 0.0,
    quantity_available: int = 0,
    category: str = "Otros",
    is_active: bool = True,
    changed_by: str = "system",
) -> dict[str, Any]:
    """Create a new billable product for a hotel."""
    db = get_database()
    import secrets
    product_id = f"PROD-{secrets.token_hex(4).upper()}"
    hotel_id = resolve_hotel_id(prop_id)

    doc = {
        "prop_id": prop_id,
        "hotel_id": hotel_id,
        "product_id": product_id,
        "name": clean_text(name),
        "description": clean_text(description),
        "unit_price": round(float(unit_price), 2),
        "quantity_available": int(quantity_available),
        "stock_tracked": bool(quantity_available > 0),
        "category": clean_text(category) or "Otros",
        "is_active": bool(is_active),
        "created_by": changed_by,
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    db.hotel_products.insert_one(doc)
    return doc


def update_hotel_product(
    prop_id: int,
    product_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
    unit_price: float | None = None,
    quantity_available: int | None = None,
    category: str | None = None,
    is_active: bool | None = None,
    changed_by: str = "system",
) -> dict[str, Any] | None:
    """Update a hotel product."""
    db = get_database()
    set_doc: dict[str, Any] = {"updated_at": now_utc(), "updated_by": changed_by}
    if name is not None:
        set_doc["name"] = clean_text(name)
    if description is not None:
        set_doc["description"] = clean_text(description)
    if unit_price is not None:
        set_doc["unit_price"] = round(float(unit_price), 2)
    if quantity_available is not None:
        set_doc["quantity_available"] = int(quantity_available)
        set_doc["stock_tracked"] = bool(quantity_available > 0)
    if category is not None:
        set_doc["category"] = clean_text(category)
    if is_active is not None:
        set_doc["is_active"] = bool(is_active)

    result = db.hotel_products.find_one_and_update(
        {"prop_id": prop_id, "product_id": product_id},
        {"$set": set_doc},
        return_document=True,
        projection={"_id": 0},
    )
    return result


def delete_hotel_product(prop_id: int, product_id: str) -> bool:
    """Delete a hotel product."""
    db = get_database()
    result = db.hotel_products.delete_one({"prop_id": prop_id, "product_id": product_id})
    return result.deleted_count > 0


def restock_product(
    prop_id: int,
    product_id: str,
    *,
    qty: float,
    unit_cost: float,
    supplier_name: str = "",
    invoice_ref: str = "",
    invoice_id: str = "",
    ledger_source_id: str | None = None,
    inventory_event_id: str | None = None,
    changed_by: str = "system",
) -> dict[str, Any] | None:
    """Manual restock for a hotel product.

    Updates quantity_available += qty and cost_price = unit_cost (last-purchase
    model) on the matching hotel_products doc. Best-effort:

    ``invoice_id`` (preferred over ``invoice_ref``) links the restock to a real
    expense invoice: it resolves ``expense_invoices`` by ``_id`` for the same
    ``prop_id`` and stores the invoice ``_id`` string as ``invoice_ref``,
    turning ``last_purchase_invoice_ref`` into a real FK instead of free text.
    An unknown or cross-property invoice id raises ``ValueError`` (→ 400).
    When ``invoice_id`` is empty, ``invoice_ref`` free text is kept as-is for
    backward compatibility with direct API/script callers.

    - Posts a balanced DR 1050 (Inventario) / CR 2010 (Ctas por Pagar Proveedores)
      journal entry via ``post_journal_entry``.
    - Records an audit row via ``register_action`` (outbox-backed).

    Failures on either side effect are logged but do NOT roll back the stock
    update — the catalog state is the source of truth; ledger/audit are
    advisory.

    Returns
    -------
    dict or None
        The updated fields + ``ledger_journal_id``. Returns ``None`` if no
        product matches (prop_id, product_id).

    Raises
    ------
    ValueError
        ``qty <= 0`` or ``unit_cost < 0``.
    """
    db = get_database()

    if qty <= 0:
        raise ValueError("qty debe ser > 0")
    if unit_cost < 0:
        raise ValueError("unit_cost debe ser >= 0")

    product = db.hotel_products.find_one(
        {"prop_id": prop_id, "product_id": product_id},
        {"_id": 0},
    )
    if not product:
        return None

    inventory_key = inventory_event_id or invoice_id
    # A vendor bill line is the business idempotency key. Retrying the same
    # invoice/product line must return the existing acquisition without incrementing
    # stock, creating another layer, or posting another journal pair.
    if invoice_id:
        existing_layer = db.fact_inventory.find_one({
            "prop_id": prop_id,
            "product_id": product_id,
            "source": "restock",
            "$or": [
                {"inventory_event_id": str(inventory_key)},
                {"invoice_ref": str(inventory_key)},
            ],
        })
        if existing_layer:
            # A retry may repair a missing/partial journal, but never receives
            # the same goods twice.
            journal_id = ""
            if ledger_source_id:
                try:
                    from src.app.modules.expenses.service.ledger_hooks import post_journal_entry
                    journal_id = post_journal_entry(
                        amount=round(float(existing_layer.get("qty_initial", 0)) * float(existing_layer.get("cost_per_unit", 0)), 2),
                        dr_account_code="1050",
                        dr_account_name="Inventario",
                        cr_account_code="2010",
                        cr_account_name="Cuentas por Pagar Proveedores",
                        description=f"Reintento restock {product_id}",
                        prop_id=prop_id,
                        source="hotel_product_restock",
                        source_id=ledger_source_id,
                    )
                except Exception:
                    logger.exception("Failed to retry ledger entry for restock %s", product_id)
            return {
                "quantity_available": product.get("quantity_available", 0),
                "cost_price": product.get("cost_price", 0),
                "default_supplier": product.get("default_supplier", ""),
                "last_purchase_invoice_ref": str(invoice_id),
                "inventory_event_id": str(inventory_key),
                "product_id": product_id,
                "prop_id": prop_id,
                "total_cost": round(float(existing_layer.get("qty_initial", 0)) * float(existing_layer.get("cost_per_unit", 0)), 2),
                "ledger_journal_id": journal_id or f"skip:hotel_product_restock/{invoice_id}",
                "fact_inventory_layer_id": existing_layer.get("layer_id", ""),
            }

    # Resolve the expense invoice link (real FK) when an id is provided.
    if invoice_id:
        try:
            oid = ObjectId(invoice_id)
        except InvalidId:
            raise ValueError("Factura de gasto no encontrada") from None
        linked = db.expense_invoices.find_one(
            {"_id": oid, "prop_id": prop_id},
            {"_id": 1, "status": 1},
        )
        if not linked:
            raise ValueError("Factura de gasto no encontrada para esta propiedad")
        # Defense-in-depth: a rejected invoice is not a valid purchase source.
        # The restock modal filters rejected invoices out of the selector, but
        # the backend must refuse a stale/forged link so a rejected expense can
        # never back a stock increase.
        if str(linked.get("status") or "").lower() == "rejected":
            raise ValueError(
                "La factura está rechazada y no puede usarse como fuente de compra"
            )
        invoice_ref = str(linked["_id"])

    old_qty = float(product.get("quantity_available", 0) or 0)
    old_cost = float(product.get("cost_price", 0.0) or 0.0)
    supplier = supplier_name or product.get("default_supplier") or ""
    total_cost = round(qty * unit_cost, 2)
    now = now_utc()
    # When the caller supplies a stable acquisition event id, claim the stock
    # delta once. A retry that already claimed this event skips the increment
    # and continues repairing the ledger/layer projection.
    claimed_event = False
    if inventory_event_id:
        event_filter = {"prop_id": prop_id, "event_id": str(inventory_event_id)}
        event_doc = db.hotel_product_restock_events.find_one(event_filter)
        if event_doc and event_doc.get("stock_applied") is True:
            claimed_event = False
        else:
            try:
                with db.client.start_session() as session:
                    with session.start_transaction():
                        current = db.hotel_product_restock_events.find_one(event_filter, session=session)
                        if current and current.get("stock_applied") is True:
                            claimed_event = False
                        else:
                            if not current:
                                db.hotel_product_restock_events.insert_one({
                                    **event_filter,
                                    "product_id": product_id,
                                    "qty": qty,
                                    "unit_cost": round(unit_cost, 2),
                                    "stock_applied": False,
                                    "created_at": now,
                                }, session=session)
                            db.hotel_products.update_one(
                                {"prop_id": prop_id, "product_id": product_id},
                                {"$inc": {"quantity_available": qty}, "$set": {
                                    "cost_price": round(unit_cost, 2),
                                    "default_supplier": supplier,
                                    "last_purchase_invoice_ref": invoice_ref or None,
                                    "last_purchase_at": now,
                                    "last_purchase_qty": qty,
                                    "updated_at": now,
                                    "updated_by": changed_by,
                                }},
                                session=session,
                            )
                            db.hotel_product_restock_events.update_one(
                                event_filter,
                                {"$set": {"stock_applied": True, "applied_at": now}},
                                session=session,
                            )
                            claimed_event = True
            except Exception:
                committed = db.hotel_product_restock_events.find_one(event_filter)
                if committed and committed.get("stock_applied") is True:
                    claimed_event = False
                else:
                    raise

    update_doc = {
        # Returned to callers/audit as the expected post-operation snapshot.
        # The actual persisted quantity is updated with $inc below.
        "quantity_available": old_qty + qty,
        "cost_price": round(unit_cost, 2),
        "default_supplier": supplier,
        "last_purchase_invoice_ref": invoice_ref or None,
        "last_purchase_at": now,
        "last_purchase_qty": qty,
        "updated_at": now,
        "updated_by": changed_by,
    }
    # Keep the stock delta atomic. The read above is only for the audit
    # snapshot; never write a stale absolute quantity over a concurrent sale or
    # restock.
    if not inventory_event_id:
        db.hotel_products.update_one(
            {"prop_id": prop_id, "product_id": product_id},
            {"$inc": {"quantity_available": qty}, "$set": {
                "cost_price": round(unit_cost, 2),
                "default_supplier": supplier,
                "last_purchase_invoice_ref": invoice_ref or None,
                "last_purchase_at": now,
                "last_purchase_qty": qty,
                "updated_at": now,
                "updated_by": changed_by,
            }},
        )

    # Post DR 1050 / CR 2010 — best-effort (stock update is the source of truth).
    journal_id = ""
    try:
        from src.app.modules.expenses.service.ledger_hooks import post_journal_entry
        journal_id = post_journal_entry(
            amount=total_cost,
            dr_account_code="1050",
            dr_account_name="Inventario",
            cr_account_code="2010",
            cr_account_name="Cuentas por Pagar Proveedores",
            description=(
                f"Restock {product_id}: {qty} unidades @ ${unit_cost:.2f} "
                f"(supplier {supplier})"
            ),
            prop_id=prop_id,
            source="hotel_product_restock",
            source_id=ledger_source_id or invoice_ref or f"manual:{product_id}:{now.isoformat()}",
        )
    except Exception:
        logger.exception("Failed to post ledger entry for restock %s", product_id)

    # Per-layer inventory trace (Fase 6): one immutable row per restock.
    # Best-effort: a missing layer means COGS report will fall back to
    # ``hotel_products.cost_price`` for this acquisition window. We insert
    # BEFORE the audit row so the audit ``diff`` block can include the
    # ``layer_id`` for traceability.
    layer_id = ""
    try:
        from src.app.modules.partner.services._inventory import (
            insert_inventory_layer,
        )
        layer = insert_inventory_layer(
            prop_id=prop_id,
            product_id=product_id,
            qty=qty,
            cost_per_unit=unit_cost,
            source="restock",
            supplier_name=supplier,
            invoice_ref=invoice_ref or "",
            inventory_event_id=str(inventory_key),
            acquired_at=now,
            created_by=changed_by,
        )
        layer_id = layer.get("layer_id", "")
    except Exception:
        logger.exception(
            "Failed to insert fact_inventory layer for restock %s", product_id
        )

    # Audit row via outbox — best-effort.
    try:
        register_action(
            prop_id=prop_id,
            entity_type="hotel_product_stock",
            entity_id=f"in:{product_id}",
            action="restock",
            summary=(
                f"Reponen {qty} unidades de {product_id} @ ${unit_cost:.2f} "
                f"(supplier {supplier})"
            ),
            changed_by=changed_by,
            diff={
                "quantity_available": {"old": old_qty, "new": old_qty + qty},
                "cost_price": {"old": old_cost, "new": round(unit_cost, 2)},
                "default_supplier": {
                    "old": product.get("default_supplier"),
                    "new": supplier,
                },
                "last_purchase_invoice_ref": {
                    "old": product.get("last_purchase_invoice_ref"),
                    "new": invoice_ref or None,
                },
            },
            metadata={
                "qty_added": qty,
                "total_cost": total_cost,
                "journal_entry_id": journal_id,
                # ``layer_id`` is the fact_inventory row this restock
                # corresponds to. Empty string if layer insert failed.
                # COGS reports will then fall back to ``hotel_products.cost_price``
                # for this acquisition window's consumption.
                "fact_inventory_layer_id": layer_id,
            },
        )
    except Exception:
        logger.exception("Failed to register audit action for restock %s", product_id)

    return {
        **update_doc,
        "product_id": product_id,
        "prop_id": prop_id,
        "total_cost": total_cost,
        "ledger_journal_id": journal_id,
        # Echo the layer_id so the restock UI can show "INV-..." in the
        # success toast, providing immediate feedback that the per-layer
        # trace is recorded (Fase 6 feature).
        "fact_inventory_layer_id": layer_id,
    }


# ─── Add-on products on active bookings ────────────────────────────────


def list_booking_line_items(booking_id: str) -> list[dict[str, Any]]:
    """Return the line items (add-on products) for a booking."""
    db = get_database()
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id},
        {"_id": 0, "line_items": 1},
    )
    if not booking:
        return []
    return booking.get("line_items", [])


def add_booking_line_item(
    booking_id: str,
    *,
    product_id: str,
    name: str,
    unit_price: float,
    quantity: int = 1,
    changed_by: str = "system",
) -> dict[str, Any] | None:
    """Add a product as a line item to an active booking.

    Validates that the product exists, checks the booking is in an active
    status (confirmed or checked_in), updates total_charges on the booking,
    and decrements quantity_available on the product (if stock-tracked).
    """
    db = get_database()

    # Validate booking is active (status, not stay_status — consistent with frontend)
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id, "status": {"$in": ["confirmed", "checked_in"]}},
        {"_id": 0, "status": 1, "prop_id": 1},
    )
    if not booking:
        return None

    # Validate product exists for this hotel — use DB values, not frontend input
    product = db.hotel_products.find_one(
        {"product_id": product_id, "prop_id": booking["prop_id"]},
        {"_id": 0, "name": 1, "unit_price": 1, "quantity_available": 1, "stock_tracked": 1},
    )
    if not product:
        return None

    # Use DB values for name and price (don't trust frontend)
    safe_name = product.get("name", name)
    safe_price = product.get("unit_price", unit_price)
    quantity = int(quantity)
    if quantity <= 0:
        return None
    total = round(float(safe_price) * quantity, 2)

    # Inventory policy is explicit. Legacy products without the field remain
    # unlimited for compatibility; tracked products continue to be tracked at
    # zero instead of silently becoming unlimited.
    stock_decremented = False
    if bool(product.get("stock_tracked", float(product.get("quantity_available", 0) or 0) > 0)):
        stock_result = db.hotel_products.update_one(
            {
                "prop_id": booking["prop_id"],
                "product_id": product_id,
                "quantity_available": {"$gte": quantity},
            },
            {"$inc": {"quantity_available": -quantity}, "$set": {"updated_at": now_utc()}},
        )
        if stock_result.modified_count != 1:
            return None
        stock_decremented = True

    import secrets
    item_id = f"LI-{secrets.token_hex(4).upper()}"
    line_item = {
        "item_id": item_id,
        "product_id": product_id,
        "name": safe_name,
        "quantity": quantity,
        "unit_price": round(float(safe_price), 2),
        "total": total,
        "added_at": now_utc(),
        "added_by": changed_by,
    }

    db.booking_orders.update_one(
        {"booking_id": booking_id},
        {
            "$push": {"line_items": line_item},
            "$inc": {"total_charges": total},
            "$set": {"updated_at": now_utc()},
        },
    )

    # Also log in status history
    db.booking_status_history.insert_one({
        "booking_id": booking_id,
        "status": booking.get("status", "confirmed"),
        "changed_at": now_utc(),
        "reason": f"add_on: {safe_name} x{quantity} = ${total}",
        "changed_by": changed_by,
        "is_test": False,
    })

    # ── Post to guest folio (same pattern as create_additional_charge) ──
    try:
        from src.app.modules.billing.service.folio import post_to_folio
        folio = post_to_folio(
            booking_id,
            posting_type="charge",
            category="Productos",
            concept=f"{safe_name} x{quantity}",
            amount=total,
            quantity=quantity,
            reference_id=item_id,
            reference_type="hotel_product",
        )
        if folio is None:
            raise RuntimeError("guest folio not found or closed")
    except Exception:
        # Do not leave an inventory decrement and a booking line without the
        # corresponding folio evidence. Roll back both local effects; a later
        # retry can safely try the complete operation again.
        db.booking_orders.update_one(
            {"booking_id": booking_id, "line_items.item_id": item_id},
            {
                "$pull": {"line_items": {"item_id": item_id}},
                "$inc": {"total_charges": -total},
            },
        )
        if stock_decremented:
            db.hotel_products.update_one(
                {"prop_id": booking["prop_id"], "product_id": product_id},
                {"$inc": {"quantity_available": quantity}},
            )
        logger.exception("Failed to auto-post product to folio for booking %s", booking_id)
        return None

    # ── Sync with active invoice (if one exists) ──
    try:
        inv = db.reservation_invoices.find_one(
            {"booking_id": booking_id, "status": "issued"},
            {"line_items": 1, "room_subtotal": 1, "extras_total": 1, "subtotal": 1, "taxes": 1, "total": 1},
        )
        if inv:
            invoice_item = {
                "item_id": item_id,
                "type": "hotel_product",
                "name": safe_name,
                "quantity": quantity,
                "unit_price": round(float(safe_price), 2),
                "total": total,
                "category": "Productos",
                "created_at": now_utc(),
            }
            combined = (inv.get("line_items") or []) + [invoice_item]
            extras_total = round(
                sum(float(it.get("total", 0)) for it in combined if it.get("type") != "room"), 2
            )
            room_subtotal = inv.get("room_subtotal", 0) or 0
            new_subtotal = round(room_subtotal + extras_total, 2)
            new_taxes = round(new_subtotal * 0.16, 2)
            new_total = round(new_subtotal + new_taxes, 2)

            inv_update = {
                "$set": {
                    "line_items": combined,
                    "extras_total": extras_total,
                    "subtotal": new_subtotal,
                    "taxes": new_taxes,
                    "total": new_total,
                    "updated_at": now_utc(),
                }
            }
            db.reservation_invoices.update_one({"_id": inv["_id"]}, inv_update)
            db.fact_reservation_invoices.update_one({"_id": inv["_id"]}, inv_update)
    except Exception:
        logger.exception(
            "Failed to sync product to invoice for booking %s", booking_id
        )

    return line_item


def remove_booking_line_item(
    booking_id: str,
    item_id: str,
    *,
    changed_by: str = "system",
) -> bool:
    """Remove a line item from a booking, restoring total_charges and inventory."""
    db = get_database()

    # Read the line item first to get its total and product_id
    booking = db.booking_orders.find_one(
        {"booking_id": booking_id, "line_items.item_id": item_id},
        {"_id": 0, "prop_id": 1, "line_items": 1},
    )
    item = None
    if booking:
        for li in booking.get("line_items", []):
            if li.get("item_id") == item_id:
                item = li
                break

    # Build atomic update: $pull + $inc + $set in one operation
    item_total = item.get("total", 0) if item else 0
    update_op: dict[str, Any] = {
        "$pull": {"line_items": {"item_id": item_id}},
        "$set": {"updated_at": now_utc()},
    }
    if item_total:
        update_op["$inc"] = {"total_charges": -item_total}

    result = db.booking_orders.update_one(
        {"booking_id": booking_id},
        update_op,
    )

    if result.modified_count > 0:
        # Restore inventory (separate collection — can't be atomic with booking update)
        if item:
            pid = item.get("product_id", "")
            if pid:
                product = db.hotel_products.find_one(
                    {"prop_id": booking.get("prop_id"), "product_id": pid},
                    {"stock_tracked": 1},
                )
                if product and product.get("stock_tracked") is True:
                    qty = item.get("quantity", 1)
                    db.hotel_products.update_one(
                        {"prop_id": booking.get("prop_id"), "product_id": pid},
                        {"$inc": {"quantity_available": qty}},
                    )

        # ── Reverse the folio charge posted by add_booking_line_item ──
        # The add path posts to the folio keyed by item_id; removing the
        # product must post a compensating charge_reversal so the folio never
        # keeps orphan revenue. Best-effort — the booking removal already
        # succeeded; a later retry of the removal is a no-op.
        if item_total and item:
            try:
                from src.app.modules.billing.service.folio import post_to_folio
                post_to_folio(
                    booking_id,
                    posting_type="charge_reversal",
                    category="Productos",
                    concept=f"Anulación: {item.get('name', '')} x{item.get('quantity', 1)}",
                    amount=item_total,
                    quantity=int(item.get("quantity", 1) or 1),
                    reference_id=item_id,
                    reference_type="hotel_product_reversal",
                )
            except Exception:
                logger.exception("Failed to reverse folio charge for removed line item %s on booking %s", item_id, booking_id)

        # ── Sync with active invoice (mirror of the add path) ──
        try:
            inv = db.reservation_invoices.find_one(
                {"booking_id": booking_id, "status": "issued"},
                {"line_items": 1, "room_subtotal": 1, "extras_total": 1, "subtotal": 1, "taxes": 1, "total": 1},
            )
            if inv:
                combined = [li for li in (inv.get("line_items") or []) if not (isinstance(li, dict) and li.get("item_id") == item_id)]
                extras_total = round(
                    sum(float(it.get("total", 0)) for it in combined if it.get("type") != "room"), 2
                )
                room_subtotal = inv.get("room_subtotal", 0) or 0
                new_subtotal = round(room_subtotal + extras_total, 2)
                new_taxes = round(new_subtotal * 0.16, 2)
                new_total = round(new_subtotal + new_taxes, 2)

                inv_update = {
                    "$set": {
                        "line_items": combined,
                        "extras_total": extras_total,
                        "subtotal": new_subtotal,
                        "taxes": new_taxes,
                        "total": new_total,
                        "updated_at": now_utc(),
                    }
                }
                db.reservation_invoices.update_one({"_id": inv["_id"]}, inv_update)
                db.fact_reservation_invoices.update_one({"_id": inv["_id"]}, inv_update)
        except Exception:
            logger.exception(
                "Failed to sync product removal to invoice for booking %s", booking_id
            )

        db.booking_status_history.insert_one({
            "booking_id": booking_id,
            "status": "modified",
            "changed_at": now_utc(),
            "reason": f"removed_add_on: {item_id}",
            "changed_by": changed_by,
            "is_test": False,
        })
    return result.modified_count > 0


# ─── Platform Earnings ─────────────────────────────────────────────────


def record_platform_earnings(
    booking_id: str,
    prop_id: int,
    *,
    commission_pct: float,
    booking_total: float,
    commission_amount: float,
) -> dict[str, Any]:
    """Record platform earnings for a booking (called during invoice creation)."""
    db = get_database()
    existing = db.platform_earnings.find_one({"booking_id": booking_id})
    if existing:
        return existing

    doc = {
        "booking_id": booking_id,
        "prop_id": prop_id,
        "commission_pct": commission_pct,
        "booking_total": round(booking_total, 2),
        "commission_amount": round(commission_amount, 2),
        "status": "pending",
        "created_at": now_utc(),
    }
    db.platform_earnings.insert_one(doc)
    return doc


def get_platform_earnings_summary() -> dict[str, Any]:
    """Aggregate platform earnings for the dashboard."""
    db = get_database()
    pipeline = [
        {
            "$group": {
                "_id": None,
                "total_commission": {"$sum": "$commission_amount"},
                "total_bookings": {"$sum": 1},
                "avg_commission": {"$avg": "$commission_amount"},
                "pending_count": {"$sum": {"$cond": [{"$eq": ["$status", "pending"]}, 1, 0]}},
                "paid_count": {"$sum": {"$cond": [{"$eq": ["$status", "paid"]}, 1, 0]}},
            }
        }
    ]
    result = list(db.platform_earnings.aggregate(pipeline))
    if not result:
        return {
            "total_commission": 0.0,
            "total_bookings": 0,
            "avg_commission": 0.0,
            "pending_count": 0,
            "paid_count": 0,
        }
    r = result[0]
    return {
        "total_commission": round(r.get("total_commission", 0), 2),
        "total_bookings": r.get("total_bookings", 0),
        "avg_commission": round(r.get("avg_commission", 0), 2),
        "pending_count": r.get("pending_count", 0),
        "paid_count": r.get("paid_count", 0),
    }


def mark_commission_paid(booking_id: str) -> dict[str, Any] | None:
    """Mark a pending platform earning as paid."""
    db = get_database()
    result = db.platform_earnings.find_one_and_update(
        {"booking_id": booking_id, "status": "pending"},
        {"$set": {"status": "paid", "paid_at": now_utc()}},
        return_document=True,
        projection={"_id": 0},
    )
    if result:
        logger.info("Commission %s marked as paid", booking_id)
    return result


def get_weekly_earnings(
    weeks: int = 12,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict[str, Any]]:
    """Aggregate platform earnings by week.

    If start_date and end_date are provided, they take precedence.
    Otherwise, uses last N weeks from now.
    """
    db = get_database()

    if start_date and end_date:
        end = end_date
        start = start_date
    else:
        end = now_utc()
        start = end - timedelta(weeks=weeks)

    pipeline = [
        {"$match": {"created_at": {"$gte": start, "$lte": end}}},
        {
            "$group": {
                "_id": {
                    "year": {"$isoWeekYear": "$created_at"},
                    "week": {"$isoWeek": "$created_at"},
                },
                "total_commission": {"$sum": "$commission_amount"},
                "total_bookings": {"$sum": 1},
                "paid_count": {
                    "$sum": {"$cond": [{"$eq": ["$status", "paid"]}, 1, 0]}
                },
                "pending_count": {
                    "$sum": {"$cond": [{"$eq": ["$status", "pending"]}, 1, 0]}
                },
            }
        },
        {"$sort": {"_id.year": 1, "_id.week": 1}},
    ]

    results = list(db.platform_earnings.aggregate(pipeline))

    # Build a lookup of week -> data
    week_map: dict[str, dict[str, Any]] = {}
    for r in results:
        yr = r["_id"]["year"]
        wk = r["_id"]["week"]
        label = f"S{wk:02d}" if yr == end.isocalendar()[0] else f"{yr}-S{wk:02d}"
        week_map[label] = {
            "label": label,
            "total_commission": round(r.get("total_commission", 0), 2),
            "total_bookings": r.get("total_bookings", 0),
            "paid_count": r.get("paid_count", 0),
            "pending_count": r.get("pending_count", 0),
        }

    # Fill all weeks in range, even those with no data
    filled: list[dict[str, Any]] = []
    cursor = start
    while cursor <= end:
        iso = cursor.isocalendar()
        yr, wk = iso[0], iso[1]
        label = f"S{wk:02d}" if yr == end.isocalendar()[0] else f"{yr}-S{wk:02d}"
        if label in week_map:
            filled.append(week_map[label])
        else:
            filled.append({
                "label": label,
                "total_commission": 0.0,
                "total_bookings": 0,
                "paid_count": 0,
                "pending_count": 0,
            })
        cursor += timedelta(days=7)

    return filled


def list_platform_earnings(page: int = 1, page_size: int = 20) -> dict[str, Any]:
    """List all platform earnings records with pagination."""
    db = get_database()
    total = db.platform_earnings.count_documents({})
    cursor = (
        db.platform_earnings.find({}, {"_id": 0})
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = []
    for doc in cursor:
        if isinstance(doc.get("created_at"), datetime):
            doc["created_at"] = doc["created_at"].isoformat()
        # Enrich with hotel name
        hotel = db.dim_hotels.find_one(
            {"prop_id": doc.get("prop_id")},
            {"display_name": 1, "hotel_name": 1, "_id": 0},
        )
        doc["hotel_name"] = (hotel.get("display_name") or hotel.get("hotel_name") or f"Hotel {doc.get('prop_id')}") if hotel else f"Hotel {doc.get('prop_id')}"
        items.append(doc)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size) if total else 1,
    }
