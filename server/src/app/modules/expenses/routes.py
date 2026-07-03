from __future__ import annotations

from datetime import datetime, timezone
from math import ceil

from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status

from src.database.connection import get_database
from src.app.modules.expenses.schemas import (
    BudgetCreate, BudgetResponse,
    ExpenseCategoryCreate, ExpenseCategoryResponse,
    InvoiceCreate, InvoiceUpdate,
    LedgerTransactionCreate, LedgerTransactionResponse, LedgerFolioResponse,
    ModuleStatus,
)
from src.app.modules.expenses.service.collections import (
    BUDGET_COLLECTION, CATEGORIES_COLLECTION, INVOICES_COLLECTION, LEDGER_COLLECTION,
    ensure_expenses_collections, module_status,
)

router = APIRouter(prefix="/modules/expenses", tags=["modules-expenses"])
api_router = APIRouter(prefix="/api/expenses", tags=["expenses-api"])


def _enrich_invoice(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    doc["total"] = (doc.get("amount") or 0) + (doc.get("tax_amount") or 0)
    if doc.get("prop_id"):
        doc["prop_id"] = int(doc["prop_id"])
    for f in ("created_at", "updated_at", "approved_at"):
        if isinstance(doc.get(f), datetime):
            doc[f] = doc[f].isoformat()
        elif doc.get(f) is None:
            doc[f] = None
    return doc


def _enrich_category(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    if isinstance(doc.get("created_at"), datetime):
        doc["created_at"] = doc["created_at"].isoformat()
    return doc


def _enrich_budget(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    if isinstance(doc.get("created_at"), datetime):
        doc["created_at"] = doc["created_at"].isoformat()
    return doc


def _enrich_ledger(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    if doc.get("prop_id"):
        doc["prop_id"] = int(doc["prop_id"])
    for f in ("tx_date", "created_at"):
        if isinstance(doc.get(f), datetime):
            doc[f] = doc[f].isoformat()
    return doc


# ─── Module Status ───

@router.get("/status", response_model=ModuleStatus)
def expenses_module_status():
    ensure_expenses_collections()
    return module_status()


# ─── Dashboard ───

@api_router.get("/dashboard")
def expenses_dashboard():
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

    return {
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
    }


# ─── Invoice CRUD ───

@api_router.post("/invoices", status_code=201)
def create_invoice(payload: InvoiceCreate = Body(...)):
    db = get_database()
    now_dt = datetime.now(timezone.utc)
    total_amount = payload.amount + payload.tax_amount
    doc = {
        "vendor_name": payload.vendor_name, "category": payload.category,
        "description": payload.description, "amount": payload.amount,
        "tax_amount": payload.tax_amount, "total": total_amount,
        "status": "pending", "invoice_date": payload.invoice_date,
        "due_date": payload.due_date, "approved_by": None, "approved_at": None,
        "notes": payload.notes, "prop_id": payload.prop_id,
        "created_at": now_dt, "updated_at": now_dt,
    }
    result = db[INVOICES_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _enrich_invoice(doc)


@api_router.get("/invoices")
def list_invoices(
    status_filter: str | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None),
    vendor: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    db = get_database()
    query: dict = {}
    if status_filter: query["status"] = status_filter
    if category: query["category"] = category
    if vendor: query["vendor_name"] = {"$regex": vendor, "$options": "i"}
    total = db[INVOICES_COLLECTION].count_documents(query)
    cursor = db[INVOICES_COLLECTION].find(query).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size)
    items = [_enrich_invoice(doc) for doc in cursor]
    return {
        "items": items, "total": total, "page": page, "page_size": page_size,
        "total_pages": max(1, ceil(total / page_size)) if total else 1,
        "has_next": page * page_size < total, "has_prev": page > 1,
    }


@api_router.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: str = Path(...)):
    db = get_database()
    try: doc = db[INVOICES_COLLECTION].find_one({"_id": ObjectId(invoice_id)})
    except Exception: raise HTTPException(status_code=404, detail="Factura no encontrada")
    if not doc: raise HTTPException(status_code=404, detail="Factura no encontrada")
    return _enrich_invoice(doc)


@api_router.put("/invoices/{invoice_id}")
def update_invoice(invoice_id: str = Path(...), payload: InvoiceUpdate = Body(...)):
    db = get_database()
    try: oid = ObjectId(invoice_id)
    except Exception: raise HTTPException(status_code=404, detail="Factura no encontrada")
    update = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if not update: raise HTTPException(status_code=400, detail="No hay campos para actualizar")
    update["updated_at"] = datetime.now(timezone.utc)
    if "amount" in update or "tax_amount" in update:
        current = db[INVOICES_COLLECTION].find_one({"_id": oid}, {"amount": 1, "tax_amount": 1})
        amt = update.get("amount", current["amount"] if current else 0)
        tax = update.get("tax_amount", current["tax_amount"] if current else 0)
        update["total"] = amt + tax
    if update.get("status") == "approved" and not update.get("approved_by"):
        update["approved_at"] = datetime.now(timezone.utc)
        update["approved_by"] = "system"
    result = db[INVOICES_COLLECTION].update_one({"_id": oid}, {"$set": update})
    if result.matched_count == 0: raise HTTPException(status_code=404, detail="Factura no encontrada")
    doc = db[INVOICES_COLLECTION].find_one({"_id": oid})
    return _enrich_invoice(doc)


@api_router.delete("/invoices/{invoice_id}", status_code=204)
def delete_invoice(invoice_id: str = Path(...)):
    db = get_database()
    try: oid = ObjectId(invoice_id)
    except Exception: raise HTTPException(status_code=404, detail="Factura no encontrada")
    result = db[INVOICES_COLLECTION].delete_one({"_id": oid})
    if result.deleted_count == 0: raise HTTPException(status_code=404, detail="Factura no encontrada")


# ─── Categories / Budget ───

@api_router.get("/categories")
def list_categories():
    db = get_database()
    cursor = db[CATEGORIES_COLLECTION].find().sort("name", 1)
    result = []
    for cat in cursor:
        cat = _enrich_category(cat)
        spent_agg = db[INVOICES_COLLECTION].aggregate([
            {"$match": {"category": cat["name"], "status": {"$in": ["approved", "paid"]}}},
            {"$group": {"_id": None, "total": {"$sum": "$total"}}},
        ])
        spent_list = list(spent_agg)
        cat["spent"] = round(spent_list[0]["total"], 2) if spent_list else 0
        cat["remaining"] = round(cat["budget"] - cat["spent"], 2)
        result.append(cat)
    return result


@api_router.post("/categories", status_code=201)
def create_category(payload: ExpenseCategoryCreate = Body(...)):
    db = get_database()
    existing = db[CATEGORIES_COLLECTION].find_one({"name": payload.name})
    if existing: raise HTTPException(status_code=409, detail="La categoría ya existe")
    doc = {"name": payload.name, "description": payload.description, "budget": payload.budget,
           "spent": 0, "remaining": payload.budget, "created_at": datetime.now(timezone.utc)}
    result = db[CATEGORIES_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _enrich_category(doc)


@api_router.post("/budget", status_code=201)
def create_budget(payload: BudgetCreate = Body(...)):
    db = get_database()
    existing = db[BUDGET_COLLECTION].find_one({"department": payload.department, "period": payload.period})
    if existing: raise HTTPException(status_code=409, detail=f"Ya existe un presupuesto para {payload.department} en {payload.period}")
    doc = {"department": payload.department, "period": payload.period, "amount": payload.amount,
           "spent": 0, "remaining": payload.amount, "description": payload.description,
           "created_at": datetime.now(timezone.utc)}
    result = db[BUDGET_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _enrich_budget(doc)


@api_router.get("/budget")
def list_budget(period: str | None = Query(default=None)):
    db = get_database()
    query = {}
    if period: query["period"] = period
    cursor = db[BUDGET_COLLECTION].find(query).sort("period", -1)
    return [_enrich_budget(doc) for doc in cursor]


# ═══════════════════════════════════════════════════════════
# Libro Mayor / Ledger  (AG Grid-powered)
# ═══════════════════════════════════════════════════════════

@api_router.get("/ledger")
def list_ledger(
    prop_id: int | None = Query(default=None, ge=1),
    folio_ref: str | None = Query(default=None),
    account_code: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    sort_field: str = Query(default="tx_date"),
    sort_order: str = Query(default="desc"),
):
    """Paginated ledger with server-side sorting and filtering for AG Grid."""
    db = get_database()
    query: dict = {}
    if prop_id: query["prop_id"] = prop_id
    if folio_ref: query["folio_ref"] = folio_ref
    if account_code: query["account_code"] = account_code
    if status_filter: query["status"] = status_filter
    if search:
        query["$or"] = [
            {"description": {"$regex": search, "$options": "i"}},
            {"folio_ref": {"$regex": search, "$options": "i"}},
            {"account_name": {"$regex": search, "$options": "i"}},
            {"user": {"$regex": search, "$options": "i"}},
        ]

    sort_dir = -1 if sort_order == "desc" else 1
    total = db[LEDGER_COLLECTION].count_documents(query)

    # Running balance: sum all debits - credits before current page
    running_balance_pipeline = [
        {"$match": query},
        {"$group": {"_id": None, "balance": {"$sum": {"$subtract": ["$debit", "$credit"]}}}},
    ]
    balance_agg = list(db[LEDGER_COLLECTION].aggregate(running_balance_pipeline))
    running_balance = balance_agg[0]["balance"] if balance_agg else 0

    cursor = (
        db[LEDGER_COLLECTION]
        .find(query)
        .sort(sort_field, sort_dir)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_enrich_ledger(doc) for doc in cursor]

    # Compute cumulative balance for each row
    cumulative = running_balance if sort_dir == -1 else 0
    for item in items:
        if sort_dir == -1:
            item["balance"] = round(cumulative, 2)
            cumulative -= item["debit"] - item["credit"]
        else:
            cumulative += item["debit"] - item["credit"]
            item["balance"] = round(cumulative, 2)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, ceil(total / page_size)) if total else 1,
        "has_next": page * page_size < total,
        "has_prev": page > 1,
    }


@api_router.get("/ledger/folios")
def list_active_folios(
    prop_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
):
    """Return active folios with guest info and balances for the right sidebar panel."""
    db = get_database()
    match: dict = {}
    if prop_id: match["prop_id"] = prop_id

    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": "$folio_ref",
            "balance": {"$sum": {"$subtract": ["$debit", "$credit"]}},
            "count": {"$sum": 1},
            "last_tx": {"$max": "$tx_date"},
        }},
        {"$sort": {"last_tx": -1}},
        {"$skip": (page - 1) * page_size},
        {"$limit": page_size},
    ]
    folios = list(db[LEDGER_COLLECTION].aggregate(pipeline))

    result = []
    for f in folios:
        folio_ref = f["_id"]
        # Get guest info from most recent transaction for this folio
        last_tx = db[LEDGER_COLLECTION].find_one(
            {"folio_ref": folio_ref},
            sort=[("tx_date", -1)],
            projection={"folio_ref": 1},
        )
        result.append({
            "folio_ref": folio_ref,
            "guest_name": f"Folio {folio_ref}",
            "room": "",
            "check_in": "",
            "check_out": "",
            "balance": round(f["balance"], 2),
            "transaction_count": f["count"],
        })

    return {
        "items": result,
        "page": page,
        "page_size": page_size,
        "total": len(result),
    }


@api_router.get("/ledger/summary")
def ledger_summary(prop_id: int | None = Query(default=None, ge=1)):
    """Return KPI summary for the ledger header: totals, budget, pending."""
    db = get_database()
    match: dict = {}
    if prop_id: match["prop_id"] = prop_id

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

    pending = db[LEDGER_COLLECTION].count_documents({**match, "status": "pending"})
    audited = db[LEDGER_COLLECTION].count_documents({**match, "status": "audited"})
    discrepancy = db[LEDGER_COLLECTION].count_documents({**match, "status": "discrepancy"})

    return {
        "total_debits": round(data["total_debits"], 2),
        "total_credits": round(data["total_credits"], 2),
        "net_balance": round(data["total_debits"] - data["total_credits"], 2),
        "transaction_count": data["count"],
        "pending_count": pending,
        "audited_count": audited,
        "discrepancy_count": discrepancy,
    }
