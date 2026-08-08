from __future__ import annotations

import logging
from datetime import datetime, timezone
from math import ceil
from typing import Any

from bson import ObjectId

from bson.errors import InvalidId
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Request

from src.app.core.constants import DEFAULT_LEDGER_PAGE_SIZE
from src.database.connection import get_database
from src.app.modules.expenses.schemas import (
    BalanceSheetResponse,
    BudgetCreate,
    BudgetListResponse,
    BudgetResponse,
    ChartOfAccountsResponse,
    DashboardResponse,
    ExpenseCategoryCreate,
    ExpenseCategoryResponse,
    FolioPaymentResponse,
    FolioPostingsResponse,
    FolioTransferResponse,
    IncomeStatementResponse,
    InvoiceCreate,
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceUpdate,
    LedgerFolioListResponse,
    LedgerFolioResponse,
    LedgerListResponse,
    LedgerSummaryResponse,
    LedgerTransactionResponse,
    ModuleStatus,
    TrialBalanceResponse,
)
from src.app.modules.billing.schemas import InvoiceCreate as BillingInvoiceCreate, PaymentCreate
from src.app.modules.expenses.service.collections import (
    BUDGET_COLLECTION, CATEGORIES_COLLECTION, CHART_OF_ACCOUNTS, INVOICES_COLLECTION, LEDGER_COLLECTION,
    ensure_expenses_collections, module_status,
)
from src.app.modules.partner.services.audit import register_action
from src.app.modules.partner.services.hotel_products import restock_product
from src.app.security.dependencies import require_permission
from src.app.core.types import to_json_safe

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/modules/expenses", tags=["modules-expenses"])
api_router = APIRouter(prefix="/api/expenses", tags=["expenses-api"])


# ─── Pydantic *Response models rebuild (Fase 5/6) ────────────────────────────
# Imports above + explicit rebuild below. `from __future__ import annotations`
# defers ALL type hints as forward-ref strings, so Pydantic v2 needs an eager
# rebuild to resolve ObjectIdStr (Annotated[str, BeforeValidator(...)]).

ExpenseCategoryResponse.model_rebuild()
InvoiceResponse.model_rebuild()
InvoiceListResponse.model_rebuild()
BudgetResponse.model_rebuild()
BudgetListResponse.model_rebuild()
LedgerTransactionResponse.model_rebuild()
LedgerListResponse.model_rebuild()
LedgerFolioResponse.model_rebuild()
LedgerFolioListResponse.model_rebuild()
FolioPostingsResponse.model_rebuild()
LedgerSummaryResponse.model_rebuild()
FolioPaymentResponse.model_rebuild()
FolioTransferResponse.model_rebuild()
TrialBalanceResponse.model_rebuild()
IncomeStatementResponse.model_rebuild()
BalanceSheetResponse.model_rebuild()
DashboardResponse.model_rebuild()
ChartOfAccountsResponse.model_rebuild()


def _resolve_category_id(category_name: str) -> ObjectId | None:
    """Resolve a category name to its ObjectId from expense_categories."""
    if not category_name:
        return None
    db = get_database()
    cat = db[CATEGORIES_COLLECTION].find_one({"name": category_name}, {"_id": 1})
    return cat["_id"] if cat else None


def _enrich_invoice(doc: dict) -> dict:
    """Strip _id conversion (Pydantic ObjectIdStr handles it); keep totals and datetime ISO."""
    doc["total"] = (doc.get("amount") or 0) + (doc.get("tax_amount") or 0)
    _enrich_product_lines(doc)
    pid = doc.get("prop_id")
    if pid is not None and not isinstance(pid, (ObjectId, str)):
        try:
            doc["prop_id"] = int(pid)
        except (TypeError, ValueError):
            # ObjectId (post-FK migration) — leave for ObjectIdStr validator
            pass
    for f in ("created_at", "updated_at", "approved_at"):
        if isinstance(doc.get(f), datetime):
            doc[f] = doc[f].isoformat()
        elif doc.get(f) is None:
            doc[f] = None
    return doc


def _enrich_product_lines(doc: dict) -> dict:
    """Attach live inventory context to each restock line (reverse view).

    Each ``product_lines`` entry already stores the purchase snapshot (name,
    qty, unit_cost, line_total, restocked). This adds the product's CURRENT
    stock and cost so the invoice detail can show "stock now" without a
    second request. Product deleted meanwhile → ``stock_now``/``cost_now``
    are None (the historical line stays visible).
    """
    lines = doc.get("product_lines")
    if not lines:
        return doc
    db = get_database()
    prop_id = doc.get("prop_id")
    for line in lines:
        line["stock_now"] = None
        line["cost_now"] = None
        pid = line.get("product_id")
        if not pid or prop_id is None:
            continue
        product = db.hotel_products.find_one(
            {"prop_id": prop_id, "product_id": pid},
            {"quantity_available": 1, "cost_price": 1},
        )
        if not product:
            continue
        line["stock_now"] = round(float(product.get("quantity_available") or 0), 2)
        line["cost_now"] = round(float(product.get("cost_price") or 0.0), 2)
    return doc


def _enrich_category(doc: dict) -> dict:
    """Strip _id conversion (Pydantic ObjectIdStr handles it); keep datetime ISO."""
    if isinstance(doc.get("created_at"), datetime):
        doc["created_at"] = doc["created_at"].isoformat()
    return doc


def _enrich_budget(doc: dict) -> dict:
    """Strip _id conversion (Pydantic ObjectIdStr handles it); keep datetime ISO."""
    if isinstance(doc.get("created_at"), datetime):
        doc["created_at"] = doc["created_at"].isoformat()
    return doc


def _enrich_ledger(doc: dict) -> dict:
    """Strip _id conversion (Pydantic ObjectIdStr handles it); keep datetime ISO + prop_id cast."""
    pid = doc.get("prop_id")
    if pid is not None and not isinstance(pid, (ObjectId, str)):
        try:
            doc["prop_id"] = int(pid)
        except (TypeError, ValueError):
            # ObjectId (post-FK migration) — leave for ObjectIdStr validator
            pass
    for f in ("tx_date", "created_at"):
        if isinstance(doc.get(f), datetime):
            doc[f] = doc[f].isoformat()
    return doc


def _unwrap_query(value: Any) -> Any:
    """Normalize a fastapi.params.Param INSTANCE back to its declared default.

    Why this exists: ``list_ledger`` is annotated with FastAPI Query defaults
    (``prop_id: int = Query(default=0, ge=0)``, ``status_filter: str | None =
    Query(default=None, alias="status")``, ...). When FastAPI dispatches a
    request it resolves them to runtime values BEFORE calling the function, so
    the function body always sees scalars.

    BUT ``ledger_transactions_by_prop`` and other by-prop route aliases
    call ``list_ledger(prop_id=…, accounting_period=…, page=…, …)`` directly
    from Python. For kwargs the caller did NOT pass, Python falls back to the
    function's signature default, which is the raw ``Query(default=None)``
    OBJECT, not the value the Query was supposed to represent. BSON encoder
    then crashes with ``InvalidDocument: cannot encode object: Query(None)``.

    This helper unwraps any such Param instance to its ``.default`` value.
    Belt-and-suspenders guard for fastapi.route-from-route calls.
    """
    from fastapi.params import Param  # local import to avoid module-level cycle

    if isinstance(value, Param):
        return value.default
    return value


# ─── Module Status ───

@router.get("/status", response_model=ModuleStatus)
def expenses_module_status():
    ensure_expenses_collections()
    return module_status()


# ─── Dashboard ───

@api_router.get("/dashboard", response_model=DashboardResponse)
def expenses_dashboard(
    request: Request,
    prop_id: int | None = Query(default=None, ge=1),
):
    """Return expense KPIs: total, by category, pending approval, budget execution."""
    db = get_database()
    now = datetime.now(timezone.utc)
    current_q = f"Q{(now.month - 1) // 3 + 1}-{now.year}"

    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_pipeline = [
        {"$match": {"created_at": {"$gte": month_start}}},
        {"$group": {"_id": None, "total": {"$sum": "$total"}}},
    ]
    month_agg = list(db[INVOICES_COLLECTION].aggregate(month_pipeline))
    month_total = month_agg[0]["total"] if month_agg else 0

    pending = db[INVOICES_COLLECTION].count_documents({"status": "pending"})
    pending_value_pipeline = [
        {"$match": {"status": "pending"}},
        {"$group": {"_id": None, "total": {"$sum": "$total"}}},
    ]
    pending_agg = list(db[INVOICES_COLLECTION].aggregate(pending_value_pipeline))
    pending_value = pending_agg[0]["total"] if pending_agg else 0

    budget_pipeline = [
        {"$match": {"period": current_q}},
        {"$group": {"_id": None, "total_budget": {"$sum": "$amount"}}},
    ]
    budget_agg = list(db[BUDGET_COLLECTION].aggregate(budget_pipeline))
    total_budget = budget_agg[0]["total_budget"] if budget_agg else 0

    spent_pipeline = [
        {"$match": {"status": {"$in": ["approved", "paid"]}}},
        {"$group": {"_id": None, "total": {"$sum": "$total"}}},
    ]
    spent_agg = list(db[INVOICES_COLLECTION].aggregate(spent_pipeline))
    total_spent = spent_agg[0]["total"] if spent_agg else 0
    budget_pct = round((total_spent / total_budget * 100), 1) if total_budget > 0 else 0

    cat_pipeline = [
        {"$group": {"_id": "$category", "total": {"$sum": "$total"}, "count": {"$sum": 1}}},
        {"$sort": {"total": -1}},
    ]
    by_category = list(db[INVOICES_COLLECTION].aggregate(cat_pipeline))

    monthly_pipeline = [
        {"$match": {"status": {"$in": ["approved", "paid"]}}},
        {"$group": {"_id": {"$dateToString": {"format": "%Y-%m", "date": "$created_at"}}, "total": {"$sum": "$total"}}},
        {"$sort": {"_id": 1}},
        {"$limit": 6},
    ]
    monthly_agg = list(db[INVOICES_COLLECTION].aggregate(monthly_pipeline))
    monthly = [{"month": m["_id"], "total": round(m["total"], 2)} for m in monthly_agg]

    user = getattr(request.state, "current_user", None) or {}
    register_action(
        prop_id=prop_id or 0,
        entity_type="expenses_dashboard",
        entity_id="dashboard",
        action="read",
        summary="Consulta de dashboard de gastos",
        changed_by=user.get("username", "anonymous"),
        metadata={"prop_id": prop_id, "url": str(request.url)},
    )
    return DashboardResponse.model_validate({
        "month_total": round(month_total, 2),
        "pending_count": pending,
        "pending_value": round(pending_value, 2),
        "total_budget": round(total_budget, 2),
        "total_spent": round(total_spent, 2),
        "budget_execution_pct": budget_pct,
        "budget_remaining": round(total_budget - total_spent, 2),
        "monthly_breakdown": monthly,
        "by_category": [
            {"category": c["_id"], "total": round(c["total"], 2), "count": c["count"]}
            for c in by_category
        ],
    })


# ─── Invoice CRUD ───

@api_router.post("/invoices", status_code=201, response_model=InvoiceResponse)
def create_invoice(
    payload: InvoiceCreate = Body(...),
    current_user: dict = Depends(require_permission("revenue.manage")),
):
    db = get_database()
    now_dt = datetime.now(timezone.utc)

    # Resolve + validate product lines BEFORE any write. Each line must point
    # to a real product of the target hotel; when lines are present the
    # invoice amount is recomputed as their sum (the invoice is the purchase
    # document backing the goods received) so there is no double entry.
    product_lines: list[dict[str, Any]] = []
    amount = payload.amount
    if payload.product_lines:
        if not payload.prop_id:
            raise HTTPException(
                status_code=400,
                detail="Selecciona una propiedad para registrar líneas de producto.",
            )
        resolved: list[dict[str, Any]] = []
        for line in payload.product_lines:
            product = db.hotel_products.find_one(
                {"prop_id": payload.prop_id, "product_id": line.product_id},
                {"_id": 0, "name": 1},
            )
            if not product:
                raise HTTPException(
                    status_code=400,
                    detail=f"Producto {line.product_id} no encontrado en esta propiedad",
                )
            line_total = round(float(line.qty) * float(line.unit_cost), 2)
            resolved.append({
                "product_id": line.product_id,
                "name": product.get("name") or line.product_id,
                "qty": round(float(line.qty), 2),
                "unit_cost": round(float(line.unit_cost), 2),
                "line_total": line_total,
            })
        product_lines = resolved
        amount = round(sum(l["line_total"] for l in resolved), 2)

    total_amount = amount + payload.tax_amount
    category_id = _resolve_category_id(payload.category)
    doc = {
        "vendor_name": payload.vendor_name, "category": payload.category,
        "category_id": category_id,
        "description": payload.description, "amount": amount,
        "tax_amount": payload.tax_amount, "total": total_amount,
        "status": "pending", "invoice_date": payload.invoice_date,
        "due_date": payload.due_date, "approved_by": None, "approved_at": None,
        "notes": payload.notes, "prop_id": payload.prop_id,
        "product_lines": product_lines,
        "created_at": now_dt, "updated_at": now_dt,
    }
    result = db[INVOICES_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id

    # Auto-restock each line in one step: stock increment + cost_price update
    # + fact_inventory layer + DR 1050 / CR 2010 ledger entry, all linked to
    # THIS invoice id (real FK).
    #
    # Accounting invariant: these restock postings are the SOLE ledger event
    # for product-backed invoices — expense invoices never carry an
    # ``invoice_number``, which is what keeps ``ledger_hooks`` from also
    # posting AP (it returns early when ``invoice_number`` is empty). If a
    # future change starts generating invoice numbers on expense invoices,
    # this coupling must be revisited to avoid double-posting CR 2010.
    #
    # Lines were pre-validated, so a failure here is a DB hiccup; the invoice
    # remains the document of truth (best-effort, the same rule restock_product
    # itself follows for ledger/audit). Each line is stamped ``restocked`` so
    # a failure is observable on the wire and persisted, not just logged.
    if product_lines:
        final_lines: list[dict[str, Any]] = []
        for line in product_lines:
            try:
                restock_product(
                    payload.prop_id,
                    line["product_id"],
                    qty=line["qty"],
                    unit_cost=line["unit_cost"],
                    supplier_name=payload.vendor_name,
                    invoice_id=str(result.inserted_id),
                    changed_by=current_user.get("username", "system"),
                )
                final_lines.append({**line, "restocked": True})
            except Exception:
                logger.exception(
                    "Auto-restock failed for line %s of invoice %s",
                    line["product_id"], result.inserted_id,
                )
                final_lines.append({**line, "restocked": False})
        db[INVOICES_COLLECTION].update_one(
            {"_id": result.inserted_id},
            {"$set": {"product_lines": final_lines}},
        )
        product_lines = final_lines
        doc["product_lines"] = final_lines

    enriched = _enrich_invoice(doc)
    diff = {
        k: {"old": None, "new": v}
        for k, v in doc.items()
        if k not in ("_id", "created_at", "updated_at", "approved_by", "approved_at") and v is not None
    }
    register_action(
        prop_id=payload.prop_id or 0,
        entity_type="expense_invoice",
        entity_id=str(result.inserted_id),
        action="create",
        summary=f"Creación de factura de gasto: {payload.vendor_name} (${total_amount:,.2f})",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    return InvoiceResponse.model_validate(enriched)


@api_router.get("/invoices", response_model=InvoiceListResponse)
def list_invoices(
    request: Request,
    status_filter: str | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None),
    category_id: str | None = Query(default=None),
    vendor: str | None = Query(default=None),
    prop_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    db = get_database()
    query: dict = {}
    if status_filter:
        # Comma-separated CSV (e.g. ``pending,approved,paid``) → $in, so invoice
        # pickers (restock modal, etc.) can exclude rejected invoices as purchase
        # sources in ONE round trip. A plain single status keeps working.
        statuses = [s.strip() for s in status_filter.split(",") if s.strip()]
        # Guard: an empty/whitespace-only CSV (e.g. ``status=,"``) means "no
        # filter", not ``$in: []`` (which would silently match nothing).
        if statuses:
            if len(statuses) == 1:
                query["status"] = statuses[0]
            else:
                query["status"] = {"$in": statuses}
    if category:
        query["category"] = category
    if category_id:
        try:
            query["category_id"] = ObjectId(category_id)
        except InvalidId:
            pass
    if vendor:
        query["vendor_name"] = {"$regex": vendor, "$options": "i"}
    if prop_id is not None:
        query["prop_id"] = prop_id
    total = db[INVOICES_COLLECTION].count_documents(query)
    cursor = db[INVOICES_COLLECTION].find(query).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size)
    items = [_enrich_invoice(doc) for doc in cursor]
    user = getattr(request.state, "current_user", None) or {}
    # Belt-and-suspenders: defensive JSON-safe wrap (ObjectId → str, datetime → isoformat)
    # catches anything _enrich_invoice may have missed (e.g. nested ObjectIds).
    items = [to_json_safe(it) for it in items]
    register_action(
        prop_id=prop_id or 0,
        entity_type="expense_invoice",
        entity_id="list",
        action="read",
        summary=f"Listado de facturas de gasto (total={total}, page={page})",
        changed_by=user.get("username", "anonymous"),
        metadata={
            "status_filter": status_filter,
            "category": category,
            "vendor": vendor,
            "prop_id": prop_id,
            "page": page,
            "page_size": page_size,
            "url": str(request.url),
        },
    )
    return InvoiceListResponse.model_validate(to_json_safe({
        "items": items, "total": total, "page": page, "page_size": page_size,
        "total_pages": max(1, ceil(total / page_size)) if total else 1,
        "has_next": page * page_size < total, "has_prev": page > 1,
    }))


@api_router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    request: Request,
    invoice_id: str = Path(...),
):
    db = get_database()
    try:
        doc = db[INVOICES_COLLECTION].find_one({"_id": ObjectId(invoice_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    if not doc:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    user = getattr(request.state, "current_user", None) or {}
    register_action(
        prop_id=(doc.get("prop_id") or 0),
        entity_type="expense_invoice",
        entity_id=invoice_id,
        action="read",
        summary=f"Consulta de factura {doc.get('vendor_name', invoice_id)}",
        changed_by=user.get("username", "anonymous"),
        metadata={"url": str(request.url)},
    )
    return InvoiceResponse.model_validate(_enrich_invoice(doc))


@api_router.put("/invoices/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(
    invoice_id: str = Path(...),
    payload: InvoiceUpdate = Body(...),
    current_user: dict = Depends(require_permission("revenue.manage")),
):
    db = get_database()
    try:
        oid = ObjectId(invoice_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    before = db[INVOICES_COLLECTION].find_one({"_id": oid})
    if not before:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    update = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if not update:
        raise HTTPException(status_code=400, detail="No hay campos para actualizar")
    update["updated_at"] = datetime.now(timezone.utc)
    if "category" in update:
        if update["category"]:
            update["category_id"] = _resolve_category_id(update["category"])
        else:
            update["category_id"] = None
    if "amount" in update or "tax_amount" in update:
        amt = update.get("amount", before["amount"])
        tax = update.get("tax_amount", before["tax_amount"])
        update["total"] = amt + tax
    if update.get("status") == "approved" and not update.get("approved_by"):
        update["approved_at"] = datetime.now(timezone.utc)
        update["approved_by"] = current_user.get("username", "system")
    db[INVOICES_COLLECTION].update_one({"_id": oid}, {"$set": update})
    doc = db[INVOICES_COLLECTION].find_one({"_id": oid})
    diff = {
        k: {"old": before.get(k), "new": v}
        for k, v in update.items()
        if k != "updated_at" and before.get(k) != v
    }
    register_action(
        prop_id=(doc.get("prop_id") or 0),
        entity_type="expense_invoice",
        entity_id=invoice_id,
        action="update",
        summary=f"Actualización de factura: {doc.get('vendor_name', invoice_id)}",
        changed_by=current_user.get("username", "system"),
        diff=diff if diff else None,
    )
    return InvoiceResponse.model_validate(_enrich_invoice(doc))


@api_router.delete("/invoices/{invoice_id}", status_code=204)
def delete_invoice(
    invoice_id: str = Path(...),
    current_user: dict = Depends(require_permission("revenue.manage")),
):
    """Returns 204 No Content — no response body; do NOT add response_model=."""
    db = get_database()
    try:
        oid = ObjectId(invoice_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    before = db[INVOICES_COLLECTION].find_one({"_id": oid})
    if not before:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    result = db[INVOICES_COLLECTION].delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    diff = {
        "deleted": {"old": before.get("status"), "new": "deleted"},
        "vendor_name": {"old": before.get("vendor_name"), "new": None},
    }
    register_action(
        prop_id=(before.get("prop_id") or 0),
        entity_type="expense_invoice",
        entity_id=invoice_id,
        action="delete",
        summary=f"Eliminación de factura: {before.get('vendor_name', invoice_id)}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )


# ─── Categories / Budget ───

@api_router.get("/categories", response_model=list[ExpenseCategoryResponse])
def list_categories(
    request: Request,
    prop_id: int | None = Query(default=None, ge=1),
):
    db = get_database()
    cursor = db[CATEGORIES_COLLECTION].find().sort("name", 1)
    result: list[dict[str, Any]] = []
    for cat_doc in cursor:
        cat_oid = cat_doc["_id"]
        cat = _enrich_category(cat_doc)
        or_filter: list = [{"category": cat["name"]}]
        if cat_oid:
            or_filter.insert(0, {"category_id": cat_oid})
        spent_agg = db[INVOICES_COLLECTION].aggregate([
            {"$match": {"$or": or_filter, "status": {"$in": ["approved", "paid"]}}},
            {"$group": {"_id": None, "total": {"$sum": "$total"}}},
        ])
        spent_list = list(spent_agg)
        cat["spent"] = round(spent_list[0]["total"], 2) if spent_list else 0
        cat["remaining"] = round(cat["budget"] - cat["spent"], 2)
        result.append(cat)
    user = getattr(request.state, "current_user", None) or {}
    register_action(
        prop_id=prop_id or 0,
        entity_type="expense_category",
        entity_id="list",
        action="read",
        summary=f"Listado de categorías de gasto ({len(result)} items)",
        changed_by=user.get("username", "anonymous"),
        metadata={"prop_id": prop_id, "count": len(result), "url": str(request.url)},
    )
    return [ExpenseCategoryResponse.model_validate(c) for c in result]


@api_router.post("/categories", status_code=201, response_model=ExpenseCategoryResponse)
def create_category(payload: ExpenseCategoryCreate = Body(...)):
    db = get_database()
    existing = db[CATEGORIES_COLLECTION].find_one({"name": payload.name})
    if existing:
        raise HTTPException(status_code=409, detail="La categoría ya existe")
    doc = {"name": payload.name, "description": payload.description, "budget": payload.budget,
           "spent": 0, "remaining": payload.budget, "created_at": datetime.now(timezone.utc)}
    result = db[CATEGORIES_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return ExpenseCategoryResponse.model_validate(_enrich_category(doc))


@api_router.post("/budget", status_code=201, response_model=BudgetResponse)
def create_budget(payload: BudgetCreate = Body(...)):
    db = get_database()
    existing = db[BUDGET_COLLECTION].find_one({"department": payload.department, "period": payload.period})
    if existing:
        raise HTTPException(status_code=409, detail=f"Ya existe un presupuesto para {payload.department} en {payload.period}")
    doc = {"department": payload.department, "period": payload.period, "amount": payload.amount,
           "spent": 0, "remaining": payload.amount, "description": payload.description,
           "created_at": datetime.now(timezone.utc)}
    result = db[BUDGET_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return BudgetResponse.model_validate(_enrich_budget(doc))


@api_router.get("/budget", response_model=BudgetListResponse)
def list_budget(period: str | None = Query(default=None)):
    db = get_database()
    query = {}
    if period:
        query["period"] = period
    cursor = db[BUDGET_COLLECTION].find(query).sort("period", -1)
    items = [BudgetResponse.model_validate(_enrich_budget(doc)) for doc in cursor]
    return BudgetListResponse.model_validate({"items": items})


# ═══════════════════════════════════════════════════════════
# Libro Mayor / Ledger  (AG Grid-powered)
# ═══════════════════════════════════════════════════════════

@api_router.get("/ledger", response_model=LedgerListResponse)
def list_ledger(
    prop_id: int = Query(default=0, ge=0),
    folio_ref: str | None = Query(default=None),
    account_code: str | None = Query(default=None),
    accounting_period: str | None = Query(default=None, description="YYYY-MM"),
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LEDGER_PAGE_SIZE, ge=1, le=200),
    sort_field: str = Query(default="tx_date"),
    sort_order: str = Query(default="desc"),
):
    """Paginated ledger with server-side sorting and filtering for AG Grid."""
    # Belt-and-suspenders: when called from another FastAPI route (e.g.
    # ``ledger_transactions_by_prop``) without explicit kwargs for the
    # optional params below, Python fills them with the raw ``Query(...)``
    # instance instead of the resolved value. ``_unwrap_query`` normalizes
    # each one to its declared ``.default``. Without this guard, BSON
    # encoding crashes on ``Query(None)`` leaking into ``query[...]``.
    prop_id = _unwrap_query(prop_id)
    folio_ref = _unwrap_query(folio_ref)
    account_code = _unwrap_query(account_code)
    accounting_period = _unwrap_query(accounting_period)
    status_filter = _unwrap_query(status_filter)
    search = _unwrap_query(search)
    page = _unwrap_query(page)
    page_size = _unwrap_query(page_size)
    sort_field = _unwrap_query(sort_field)
    sort_order = _unwrap_query(sort_order)

    db = get_database()
    query: dict = {}
    if prop_id:
        query["prop_id"] = prop_id
    if folio_ref:
        query["folio_ref"] = folio_ref
    if account_code:
        query["account_code"] = account_code
    if accounting_period:
        query["accounting_period"] = accounting_period
    if status_filter:
        query["status"] = status_filter
    if search:
        query["$or"] = [
            {"description": {"$regex": search, "$options": "i"}},
            {"folio_ref": {"$regex": search, "$options": "i"}},
            {"account_name": {"$regex": search, "$options": "i"}},
            {"account_code": {"$regex": search, "$options": "i"}},
            {"guest_name": {"$regex": search, "$options": "i"}},
            {"cost_center": {"$regex": search, "$options": "i"}},
            {"journal_entry_id": {"$regex": search, "$options": "i"}},
        ]

    sort_dir = -1 if sort_order == "desc" else 1
    total = db[LEDGER_COLLECTION].count_documents(query)
    skip = (page - 1) * page_size

    # Compute balance of all rows BEFORE the current page
    if skip > 0:
        prior_balance = sum(
            d.get("debit", 0) - d.get("credit", 0)
            for d in db[LEDGER_COLLECTION].find(
                query, {"debit": 1, "credit": 1}
            ).sort(sort_field, sort_dir).limit(skip)
        )
    else:
        prior_balance = 0

    # Total balance of ALL matching rows
    total_balance_pipeline = [
        {"$match": query},
        {"$group": {"_id": None, "balance": {"$sum": {"$subtract": ["$debit", "$credit"]}}}},
    ]
    balance_agg = list(db[LEDGER_COLLECTION].aggregate(total_balance_pipeline))
    total_balance = balance_agg[0]["balance"] if balance_agg else 0

    cursor = (
        db[LEDGER_COLLECTION]
        .find(query)
        .sort(sort_field, sort_dir)
        .skip(skip)
        .limit(page_size)
    )
    items_raw = [_enrich_ledger(doc) for doc in cursor]

    # Running balance accounting for prior pages
    if sort_dir == -1:
        cumulative = total_balance - prior_balance
        for item in items_raw:
            item["balance"] = round(cumulative, 2)
            cumulative -= item.get("debit", 0) - item.get("credit", 0)
    else:
        cumulative = prior_balance
        for item in items_raw:
            cumulative += item.get("debit", 0) - item.get("credit", 0)
            item["balance"] = round(cumulative, 2)

    items = [LedgerTransactionResponse.model_validate(to_json_safe(it)) for it in items_raw]
    return LedgerListResponse.model_validate(to_json_safe({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, ceil(total / page_size)) if total else 1,
        "has_next": page * page_size < total,
        "has_prev": page > 1,
        "total_balance": total_balance,
    }))


@api_router.get("/ledger/folios", response_model=LedgerFolioListResponse)
def list_active_folios(
    prop_id: int = Query(default=0, ge=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    status: str | None = Query(default=None),
):
    """Return guest folios with balances for the sidebar panel.

    Defaults to open folios only. Pass status=closed or omit the param
    (status=null) to see all folios.
    """
    db = get_database()
    query: dict = {}
    if status:
        query["status"] = status
    else:
        query["status"] = "open"
    if prop_id:
        query["prop_id"] = int(prop_id)

    total = db.guest_folios.count_documents(query)
    cursor = (
        db.guest_folios
        .find(query)
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )

    items_raw: list[dict[str, Any]] = []
    for f in cursor:
        items_raw.append({
            "folio_id": str(f["_id"]),
            "folio_ref": f.get("folio_number", ""),
            "guest_name": f.get("guest_name", ""),
            "room": f.get("room_label", ""),
            "check_in": f.get("check_in_date", ""),
            "check_out": f.get("check_out_date", ""),
            "balance": round(f.get("total_due", 0), 2),
            "transaction_count": f.get("posting_count", 0),
            "booking_id": f.get("booking_id", ""),
            "status": f.get("status", ""),
        })

    items = [LedgerFolioResponse.model_validate(it) for it in items_raw]
    return LedgerFolioListResponse.model_validate({
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
    })


@api_router.get("/ledger/folios/{folio_id}/postings", response_model=FolioPostingsResponse)
def get_folio_postings(folio_id: str = Path(...)):
    """Return the posting history for a guest folio."""
    from src.app.modules.billing.service.folio import get_folio_by_id

    folio = get_folio_by_id(folio_id)
    if not folio:
        raise HTTPException(status_code=404, detail="Folio no encontrado")

    postings = folio.get("postings", [])
    result: list[dict[str, Any]] = []
    for p in postings:
        posted = p.get("posted_at")
        if isinstance(posted, datetime):
            posted = posted.isoformat()
        result.append({
            "posting_id": str(p.get("posting_id", "")),
            "type": p.get("type", ""),
            "category": p.get("category", ""),
            "concept": p.get("concept", ""),
            "amount": round(p.get("amount", 0), 2),
            "quantity": p.get("quantity", 1),
            "unit_price": round(p.get("unit_price", 0), 2),
            "reference_id": p.get("reference_id", ""),
            "reference_type": p.get("reference_type", ""),
            "posted_at": posted or "",
        })

    return FolioPostingsResponse.model_validate({
        "folio_id": folio_id,
        "folio_ref": folio.get("folio_number", ""),
        "guest_name": folio.get("guest_name", ""),
        "postings": sorted(result, key=lambda x: x.get("posted_at", ""), reverse=True),
    })


@api_router.get("/ledger/summary", response_model=LedgerSummaryResponse)
def ledger_summary(prop_id: int | None = Query(default=None, ge=1)):
    """Return trial balance + KPI summary for the ledger header."""
    db = get_database()
    match: dict = {}
    if prop_id:
        match["prop_id"] = int(prop_id)

    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": None,
            "total_debits": {"$sum": "$debit"},
            "total_credits": {"$sum": "$credit"},
            "count": {"$sum": 1},
        }},
    ]
    agg = list(db[LEDGER_COLLECTION].aggregate(pipeline))
    data = agg[0] if agg else {"total_debits": 0, "total_credits": 0, "count": 0}

    revenue_pipeline = [
        {"$match": {**match, "account_code": {"$regex": "^4"}}},
        {"$group": {"_id": "$account_code", "total": {"$sum": "$credit"}}},
        {"$sort": {"total": -1}},
    ]
    revenue = list(db[LEDGER_COLLECTION].aggregate(revenue_pipeline))

    journal_pipeline = [
        {"$match": match},
        {"$group": {"_id": "$journal_entry_id"}},
        {"$count": "total"},
    ]
    journal_agg = list(db[LEDGER_COLLECTION].aggregate(journal_pipeline))
    journal_count = journal_agg[0]["total"] if journal_agg else 0

    diff = round(data["total_debits"] - data["total_credits"], 2)

    return LedgerSummaryResponse.model_validate({
        "total_debits": round(data["total_debits"], 2),
        "total_credits": round(data["total_credits"], 2),
        "trial_balance_diff": diff,
        "is_balanced": abs(diff) < 0.01,
        "transaction_count": data["count"],
        "journal_entry_count": journal_count,
        "revenue_breakdown": [
            {"account_code": r["_id"], "total": round(r["total"], 2)}
            for r in revenue
        ],
    })


@api_router.post("/ledger/folios/{folio_id}/payment", response_model=FolioPaymentResponse)
def register_folio_payment(
    folio_id: str = Path(...),
    amount: float = Body(..., gt=0),
    method: str = Body(default="cash"),
    notes: str = Body(default=""),
    paid_by: str = Body(default="staff"),
):
    """Register a payment against a guest folio."""
    from src.app.modules.billing.service.folio import get_folio_by_id, post_to_folio
    from src.app.modules.billing.service.lifecycle.invoices import create_invoice as create_billing_invoice
    from src.app.modules.billing.service.lifecycle.payments import create_payment as create_billing_payment

    folio = get_folio_by_id(folio_id)
    if not folio:
        raise HTTPException(status_code=404, detail="Folio no encontrado")
    if folio.get("status") != "open":
        raise HTTPException(status_code=400, detail="Solo se pueden pagar folios abiertos")

    booking_id = folio.get("booking_id", "")
    if not booking_id:
        raise HTTPException(status_code=400, detail="Folio sin booking_id")

    # 1. Post payment transaction to the folio (reduces balance)
    concept = f"Pago {method} por {paid_by} — {notes}" if notes else f"Pago {method} por {paid_by}"
    updated = post_to_folio(
        booking_id,
        posting_type="payment",
        category=method.title(),
        concept=concept,
        amount=amount,
        reference_id=f"PAY-{folio.get('folio_number', '')}",
        reference_type="folio_payment",
    )
    if not updated:
        raise HTTPException(status_code=500, detail="Error al registrar el pago")

    # 2. Create or find existing reservation_invoice for this booking
    db = get_database()
    invoice = db.reservation_invoices.find_one({"booking_id": booking_id})

    if not invoice:
        invoice_total = round(
            folio.get("total_room", 0)
            + folio.get("total_charges", 0)
            - folio.get("total_discounts", 0),
            2,
        )
        subtotal = round(invoice_total / 1.16, 2) if invoice_total > 0 else round(amount / 1.16, 2)
        taxes = round(invoice_total - subtotal, 2) if invoice_total > 0 else round(amount - subtotal, 2)

        invoice_result = create_billing_invoice(BillingInvoiceCreate(
            booking_id=booking_id,
            subtotal=subtotal,
            taxes=taxes,
            notes=f"Factura generada desde folio {folio.get('folio_number', '')} — Pago {method}",
        ))
        invoice_id = invoice_result.get("id", "") if invoice_result else ""
    else:
        invoice_id = str(invoice["_id"])

    # 3. Record the payment (generates ledger entries automatically)
    payment_result = create_billing_payment(PaymentCreate(
        booking_id=booking_id,
        invoice_id=invoice_id,
        amount=amount,
        method=method,
    ))

    return FolioPaymentResponse.model_validate({
        "folio_id": folio_id,
        "folio_number": folio.get("folio_number", ""),
        "new_balance": round(updated.get("total_due", 0), 2),
        "payment_amount": amount,
        "method": method,
        "invoice_id": invoice_id,
        "invoice_created": invoice is None,
        "payment_reference": (payment_result or {}).get("reference", ""),
        "payment_id": str((payment_result or {}).get("id", "") or ""),
    })


@api_router.post("/ledger/folios/{folio_id}/transfer", response_model=FolioTransferResponse)
def transfer_folio_charges(
    folio_id: str = Path(...),
    target_folio_id: str = Body(...),
    amount: float = Body(..., gt=0),
    notes: str = Body(default=""),
):
    """Transfer charges from one folio to another."""
    from src.app.modules.billing.service.folio import get_folio_by_id, post_to_folio

    source = get_folio_by_id(folio_id)
    if not source:
        raise HTTPException(status_code=404, detail="Folio origen no encontrado")
    if source.get("status") != "open":
        raise HTTPException(status_code=400, detail="Solo se pueden transferir cargos desde folios abiertos")

    target = get_folio_by_id(target_folio_id)
    if not target:
        raise HTTPException(status_code=404, detail="Folio destino no encontrado")
    if target.get("status") != "open":
        raise HTTPException(status_code=400, detail="Solo se pueden transferir cargos a folios abiertos")

    if folio_id == target_folio_id:
        raise HTTPException(status_code=400, detail="No se puede transferir al mismo folio")

    # Debit source (reduce balance): post a negative adjustment
    concept = f"Transferencia a {target.get('folio_number', '')}" + (f" — {notes}" if notes else "")
    src_result = post_to_folio(
        source.get("booking_id", ""),
        posting_type="adjustment",
        category="Transferencia",
        concept=concept,
        amount=-amount,
        reference_id=f"XFR-OUT-{source.get('folio_number', '')}",
        reference_type="folio_transfer_out",
    )
    if not src_result:
        raise HTTPException(status_code=500, detail="Error al debitar folio origen")

    # Credit target (increase balance)
    concept2 = f"Transferencia de {source.get('folio_number', '')}" + (f" — {notes}" if notes else "")
    tgt_result = post_to_folio(
        target.get("booking_id", ""),
        posting_type="adjustment",
        category="Transferencia",
        concept=concept2,
        amount=amount,
        reference_id=f"XFR-IN-{source.get('folio_number', '')}",
        reference_type="folio_transfer_in",
    )
    if not tgt_result:
        post_to_folio(
            source.get("booking_id", ""),
            posting_type="adjustment",
            category="Transferencia",
            concept=f"REVERSIÓN: {concept}",
            amount=amount,
            reference_id=f"REV-{source.get('folio_number', '')}",
            reference_type="folio_reversal",
        )
        raise HTTPException(status_code=500, detail="Error al acreditar folio destino — operación revertida")

    src_updated = get_folio_by_id(folio_id)
    tgt_updated = get_folio_by_id(target_folio_id)

    return FolioTransferResponse.model_validate({
        "source_folio_id": folio_id,
        "source_new_balance": round(src_updated.get("total_due", 0), 2) if src_updated else 0,
        "target_folio_id": target_folio_id,
        "target_new_balance": round(tgt_updated.get("total_due", 0), 2) if tgt_updated else 0,
        "amount": amount,
    })


@api_router.get("/ledger/accounts", response_model=list[dict[str, Any]])
def list_chart_of_accounts():
    """Return the full chart of accounts for the accounting ledger."""
    db = get_database()
    cursor = db[CHART_OF_ACCOUNTS].find().sort("account_code", 1)
    result: list[dict[str, Any]] = []
    for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        result.append(doc)
    return result


@api_router.get("/ledger/periods", response_model=list[str])
def list_ledger_periods(prop_id: int = Query(default=0, ge=0)):
    """Return distinct accounting periods available in the ledger."""
    db = get_database()
    match: dict = {}
    if prop_id:
        match["prop_id"] = prop_id
    periods = db[LEDGER_COLLECTION].distinct("accounting_period", match)
    return sorted([p for p in periods if p], reverse=True)


@api_router.get("/ledger/trial-balance", response_model=TrialBalanceResponse)
def trial_balance(
    prop_id: int = Query(default=0, ge=0),
    accounting_period: str | None = Query(default=None, description="YYYY-MM"),
):
    """Balance de Sumas y Saldos: agrupa débitos y créditos por cuenta contable.

    Returns every account with its total debits, total credits, and net balance.
    """
    db = get_database()
    match: dict = {}
    if prop_id:
        match["prop_id"] = int(prop_id)
    if accounting_period:
        match["accounting_period"] = accounting_period

    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": "$account_code",
            "total_debits": {"$sum": "$debit"},
            "total_credits": {"$sum": "$credit"},
            "tx_count": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]
    ledger_agg = list(db[LEDGER_COLLECTION].aggregate(pipeline))

    chart: dict[str, Any] = {}
    for doc in db[CHART_OF_ACCOUNTS].find():
        chart[doc["account_code"]] = doc

    rows: list[dict[str, Any]] = []
    total_debits = 0.0
    total_credits = 0.0

    for row in ledger_agg:
        code = row["_id"]
        acct = chart.get(code, {})
        debits = round(row["total_debits"], 2)
        credits = round(row["total_credits"], 2)
        balance = round(debits - credits, 2)
        total_debits += debits
        total_credits += credits

        rows.append({
            "account_code": code,
            "account_name": acct.get("account_name", code),
            "account_type": acct.get("account_type", ""),
            "normal_balance": acct.get("normal_balance", ""),
            "total_debits": debits,
            "total_credits": credits,
            "balance": balance,
            "tx_count": row["tx_count"],
            "is_zero_balance": abs(balance) < 0.01,
        })

    total_debits = round(total_debits, 2)
    total_credits = round(total_credits, 2)
    diff = round(total_debits - total_credits, 2)

    return TrialBalanceResponse.model_validate({
        "rows": rows,
        "totals": {
            "total_debits": total_debits,
            "total_credits": total_credits,
            "difference": diff,
            "is_balanced": abs(diff) < 0.01,
        },
        "filters": {
            "prop_id": prop_id,
            "accounting_period": accounting_period,
        },
        "account_count": len(rows),
    })


@api_router.get("/ledger/income-statement", response_model=IncomeStatementResponse)
def income_statement(
    prop_id: int = Query(default=0, ge=0),
    accounting_period: str | None = Query(default=None, description="YYYY-MM"),
):
    """Estado de Resultados (P&L): Ingresos - Costos - Descuentos = Resultado Neto."""
    db = get_database()
    match: dict = {}
    if prop_id:
        match["prop_id"] = int(prop_id)
    if accounting_period:
        match["accounting_period"] = accounting_period

    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": "$account_code",
            "account_name": {"$first": "$account_name"},
            "total_debits": {"$sum": "$debit"},
            "total_credits": {"$sum": "$credit"},
        }},
        {"$sort": {"_id": 1}},
    ]
    agg = list(db[LEDGER_COLLECTION].aggregate(pipeline))

    chart: dict[str, Any] = {}
    for doc in db[CHART_OF_ACCOUNTS].find():
        chart[doc["account_code"]] = doc

    revenue_lines: list[dict[str, Any]] = []
    cost_lines: list[dict[str, Any]] = []
    discount_lines: list[dict[str, Any]] = []

    total_revenue = 0.0
    total_costs = 0.0
    total_discounts = 0.0

    for row in agg:
        code = row["_id"]
        acct = chart.get(code, {})
        acct_type = acct.get("account_type", "")
        debits = round(row["total_debits"], 2)
        credits = round(row["total_credits"], 2)

        if acct_type == "revenue":
            net = round(credits - debits, 2)
            total_revenue += net
            revenue_lines.append({
                "account_code": code,
                "account_name": row.get("account_name") or acct.get("account_name", code),
                "debits": debits,
                "credits": credits,
                "net": net,
            })
        elif acct_type == "expense":
            net = round(debits - credits, 2)
            total_costs += net
            cost_lines.append({
                "account_code": code,
                "account_name": row.get("account_name") or acct.get("account_name", code),
                "debits": debits,
                "credits": credits,
                "net": net,
            })
        elif acct_type == "contra_revenue":
            net = round(debits - credits, 2)
            total_discounts += net
            discount_lines.append({
                "account_code": code,
                "account_name": row.get("account_name") or acct.get("account_name", code),
                "debits": debits,
                "credits": credits,
                "net": net,
            })

    total_revenue = round(total_revenue, 2)
    total_costs = round(total_costs, 2)
    total_discounts = round(total_discounts, 2)
    gross_profit = round(total_revenue - total_discounts, 2)
    net_income = round(gross_profit - total_costs, 2)

    return IncomeStatementResponse.model_validate({
        "period": accounting_period,
        "prop_id": prop_id,
        "revenue": {"lines": revenue_lines, "total": total_revenue},
        "discounts": {"lines": discount_lines, "total": total_discounts},
        "net_revenue": gross_profit,
        "costs": {"lines": cost_lines, "total": total_costs},
        "net_income": net_income,
    })


@api_router.get("/ledger/balance-sheet", response_model=BalanceSheetResponse)
def balance_sheet(
    prop_id: int = Query(default=0, ge=0),
    accounting_period: str | None = Query(default=None, description="YYYY-MM"),
):
    """Balance General: Activos = Pasivos + Patrimonio + Resultado del Período."""
    db = get_database()
    match: dict = {}
    if prop_id:
        match["prop_id"] = int(prop_id)
    if accounting_period:
        match["accounting_period"] = accounting_period

    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": "$account_code",
            "account_name": {"$first": "$account_name"},
            "total_debits": {"$sum": "$debit"},
            "total_credits": {"$sum": "$credit"},
        }},
        {"$sort": {"_id": 1}},
    ]
    agg = list(db[LEDGER_COLLECTION].aggregate(pipeline))

    chart: dict[str, Any] = {}
    for doc in db[CHART_OF_ACCOUNTS].find():
        chart[doc["account_code"]] = doc

    asset_lines: list[dict[str, Any]] = []
    liability_lines: list[dict[str, Any]] = []
    equity_lines: list[dict[str, Any]] = []

    total_assets = 0.0
    total_liabilities = 0.0
    total_equity = 0.0
    net_income = 0.0

    for row in agg:
        code = row["_id"]
        acct = chart.get(code, {})
        acct_type = acct.get("account_type", "")
        debits = round(row["total_debits"], 2)
        credits = round(row["total_credits"], 2)

        if acct_type == "asset":
            net = round(debits - credits, 2)
            total_assets += net
            asset_lines.append({
                "account_code": code,
                "account_name": row.get("account_name") or acct.get("account_name", code),
                "debits": debits,
                "credits": credits,
                "net": net,
            })
        elif acct_type == "liability":
            net = round(credits - debits, 2)
            total_liabilities += net
            liability_lines.append({
                "account_code": code,
                "account_name": row.get("account_name") or acct.get("account_name", code),
                "debits": debits,
                "credits": credits,
                "net": net,
            })
        elif acct_type == "equity":
            net = round(credits - debits, 2)
            total_equity += net
            equity_lines.append({
                "account_code": code,
                "account_name": row.get("account_name") or acct.get("account_name", code),
                "debits": debits,
                "credits": credits,
                "net": net,
            })
        elif acct_type == "revenue":
            net_income += round(credits - debits, 2)
        elif acct_type == "expense":
            net_income -= round(debits - credits, 2)
        elif acct_type == "contra_revenue":
            net_income -= round(debits - credits, 2)

    total_assets = round(total_assets, 2)
    total_liabilities = round(total_liabilities, 2)
    total_equity = round(total_equity, 2)
    net_income = round(net_income, 2)
    rhs = round(total_liabilities + total_equity + net_income, 2)

    return BalanceSheetResponse.model_validate({
        "period": accounting_period,
        "prop_id": prop_id,
        "assets": {"lines": asset_lines, "total": total_assets},
        "liabilities": {"lines": liability_lines, "total": total_liabilities},
        "equity": {"lines": equity_lines, "total": total_equity},
        "net_income": net_income,
        "total_liabilities_and_equity": rhs,
        "is_balanced": abs(total_assets - rhs) < 0.01,
    })


# ═══════════════════════════════════════════════════════════
# Ledger path-based prop_id aliases (frontend contract)
# ═══════════════════════════════════════════════════════════

@api_router.get("/ledger/chart-of-accounts", response_model=list[dict[str, Any]])
def chart_of_accounts_alias():
    """Alias for the chart of accounts endpoint used by the ledger page."""
    return list_chart_of_accounts()


@api_router.get("/ledger/{prop_id}/summary", response_model=LedgerSummaryResponse)
def ledger_summary_by_prop(prop_id: int = Path(..., ge=1)):
    """Return ledger summary for a specific property."""
    return ledger_summary(prop_id=prop_id)


@api_router.get("/ledger/{prop_id}/periods", response_model=list[str])
def ledger_periods_by_prop(prop_id: int = Path(..., ge=1)):
    """Return distinct ledger periods for a specific property."""
    return list_ledger_periods(prop_id=prop_id)


@api_router.get("/ledger/{prop_id}/transactions", response_model=LedgerListResponse)
def ledger_transactions_by_prop(
    prop_id: int = Path(..., ge=1),
    period: str | None = Query(default=None, description="YYYY-MM"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_LEDGER_PAGE_SIZE, ge=1, le=200),
    sort_by: str = Query(default="tx_date"),
    sort_dir: str = Query(default="desc"),
    search: str | None = Query(default=None),
):
    """Return ledger transactions for a specific property."""
    return list_ledger(
        prop_id=prop_id,
        accounting_period=period,
        page=page,
        page_size=page_size,
        sort_field=sort_by,
        sort_order=sort_dir,
        search=search,
    )


@api_router.get("/ledger/{prop_id}/trial-balance", response_model=TrialBalanceResponse)
def trial_balance_by_prop(
    prop_id: int = Path(..., ge=1),
    period: str | None = Query(default=None, description="YYYY-MM"),
):
    """Return trial balance for a specific property."""
    return trial_balance(prop_id=prop_id, accounting_period=period)


@api_router.get("/ledger/{prop_id}/income-statement", response_model=IncomeStatementResponse)
def income_statement_by_prop(
    prop_id: int = Path(..., ge=1),
    period: str | None = Query(default=None, description="YYYY-MM"),
):
    """Return income statement for a specific property."""
    return income_statement(prop_id=prop_id, accounting_period=period)


@api_router.get("/ledger/{prop_id}/balance-sheet", response_model=BalanceSheetResponse)
def balance_sheet_by_prop(
    prop_id: int = Path(..., ge=1),
    period: str | None = Query(default=None, description="YYYY-MM"),
):
    """Return balance sheet for a specific property."""
    return balance_sheet(prop_id=prop_id, accounting_period=period)
