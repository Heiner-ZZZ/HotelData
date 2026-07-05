from __future__ import annotations

from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Request, status

from src.database.connection import get_database
from src.app.modules.hr.schemas import (
    DepartmentCreate,
    EmployeeCreate,
    EmployeePortalResponse,
    EmployeeResponse,
    EmployeeShiftCheckIn,
    EmployeeShiftCheckOut,
    EmployeeUpdate,
    ModuleStatus,
)
from src.app.modules.hr.service.collections import (
    DEPARTMENTS_COLLECTION,
    DOCUMENTS_COLLECTION,
    EMPLOYEES_COLLECTION,
    SHIFTS_COLLECTION,
    ensure_hr_collections,
    module_status,
)
from src.app.modules.partner.services.audit import register_action
from src.app.security.dependencies import require_login

router = APIRouter(prefix="/modules/hr", tags=["modules-hr"])
api_router = APIRouter(prefix="/api/hr", tags=["hr-api"])


def _enrich_employee(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    for f in ("created_at", "updated_at"):
        if isinstance(doc.get(f), datetime):
            doc[f] = doc[f].isoformat()
    return doc


def _enrich_department(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    if isinstance(doc.get("created_at"), datetime):
        doc["created_at"] = doc["created_at"].isoformat()
    return doc


# ═══════════════════════════════════════════════════════════
# Module Status
# ═══════════════════════════════════════════════════════════

@router.get("/status", response_model=ModuleStatus)
def hr_module_status():
    ensure_hr_collections()
    return module_status()


# ═══════════════════════════════════════════════════════════
# Dashboard
# ═══════════════════════════════════════════════════════════

@api_router.get("/dashboard")
def hr_dashboard(
    request: Request,
    prop_id: int | None = Query(default=None, ge=1),
):
    """Return HR KPIs: total employees, active, by department, recent hires."""
    db = get_database()
    total = db[EMPLOYEES_COLLECTION].count_documents({})
    active = db[EMPLOYEES_COLLECTION].count_documents({"is_active": True})
    departments = list(db[DEPARTMENTS_COLLECTION].find().sort("name", 1))
    recent = list(
        db[EMPLOYEES_COLLECTION].find({"is_active": True})
        .sort("created_at", -1).limit(5)
    )
    user = getattr(request.state, "current_user", None) or {}
    register_action(
        prop_id=prop_id or 0,
        entity_type="hr_dashboard",
        entity_id="dashboard",
        action="read",
        summary="Consulta de dashboard de RRHH",
        changed_by=user.get("username", "anonymous"),
        metadata={"prop_id": prop_id, "url": str(request.url)},
    )
    return {
        "total_employees": total,
        "active_employees": active,
        "inactive_employees": total - active,
        "departments": len(departments),
        "recent_hires": [_enrich_employee(e) for e in recent],
    }


# ═══════════════════════════════════════════════════════════
# Departments  (MUST be before /{employee_id} catch-all)
# ═══════════════════════════════════════════════════════════

@api_router.get("/departments")
def list_departments(
    request: Request,
    prop_id: int | None = Query(default=None, ge=1),
):
    db = get_database()
    cursor = db[DEPARTMENTS_COLLECTION].find().sort("name", 1)
    items = [_enrich_department(d) for d in cursor]
    user = getattr(request.state, "current_user", None) or {}
    register_action(
        prop_id=prop_id or 0,
        entity_type="department",
        entity_id="list",
        action="read",
        summary=f"Listado de departamentos ({len(items)} items)",
        changed_by=user.get("username", "anonymous"),
        metadata={"prop_id": prop_id, "count": len(items), "url": str(request.url)},
    )
    return items


@api_router.post("/departments", status_code=201)
def create_department(
    payload: DepartmentCreate = Body(...),
    current_user: dict = Depends(require_login),
):
    db = get_database()
    existing = db[DEPARTMENTS_COLLECTION].find_one({"name": payload.name})
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El departamento ya existe")
    doc = {
        "name": payload.name,
        "description": payload.description,
        "head_count": 0,
        "created_at": datetime.now(timezone.utc),
    }
    result = db[DEPARTMENTS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    enriched = _enrich_department(doc)
    diff = {
        "name": {"old": None, "new": payload.name},
        "description": {"old": None, "new": payload.description},
    }
    register_action(
        prop_id=0,
        entity_type="department",
        entity_id=enriched["id"],
        action="create",
        summary=f"Creación de departamento: {payload.name}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
    return enriched


# ═══════════════════════════════════════════════════════════
# Shift Management  (MUST be before /{employee_id} catch-all)
# ═══════════════════════════════════════════════════════════

@api_router.post("/shifts/{shift_id}/check-in")
def shift_check_in(
    shift_id: str = Path(...),
    payload: EmployeeShiftCheckIn = Body(...),
    current_user: dict = Depends(require_login),
):
    """Record an employee check-in for a shift."""
    db = get_database()
    try:
        shift_oid = ObjectId(shift_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno no encontrado")

    now = datetime.now(timezone.utc)
    timestamp = now.isoformat()
    if payload.timestamp:
        timestamp = payload.timestamp

    before = db[SHIFTS_COLLECTION].find_one_and_update(
        {"_id": shift_oid, "status": "pending"},
        {"$set": {
            "status": "active",
            "actual_check_in": timestamp,
            "check_in_notes": payload.notes,
            "updated_at": now,
        }},
    )
    if not before:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El turno no está pendiente o no existe",
        )

    diff = {
        "status": {"old": before.get("status"), "new": "active"},
        "actual_check_in": {"old": before.get("actual_check_in"), "new": timestamp},
    }
    register_action(
        prop_id=0,
        entity_type="shift",
        entity_id=shift_id,
        action="update",
        summary=f"Check-in de turno {shift_id}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
        metadata={"employee_id": payload.employee_id, "notes": payload.notes},
    )
    return {"shift_id": str(shift_id), "status": "active", "check_in": timestamp}


@api_router.post("/shifts/{shift_id}/check-out")
def shift_check_out(
    shift_id: str = Path(...),
    payload: EmployeeShiftCheckOut = Body(...),
    current_user: dict = Depends(require_login),
):
    """Record an employee check-out for a shift."""
    db = get_database()
    try:
        shift_oid = ObjectId(shift_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno no encontrado")

    now = datetime.now(timezone.utc)
    timestamp = now.isoformat()
    if payload.timestamp:
        timestamp = payload.timestamp

    before = db[SHIFTS_COLLECTION].find_one_and_update(
        {"_id": shift_oid, "status": "active"},
        {"$set": {
            "status": "completed",
            "actual_check_out": timestamp,
            "check_out_notes": payload.notes,
            "updated_at": now,
        }},
    )
    if not before:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El turno no está activo o no existe",
        )

    diff = {
        "status": {"old": before.get("status"), "new": "completed"},
        "actual_check_out": {"old": before.get("actual_check_out"), "new": timestamp},
    }
    register_action(
        prop_id=0,
        entity_type="shift",
        entity_id=shift_id,
        action="update",
        summary=f"Check-out de turno {shift_id}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
        metadata={"employee_id": payload.employee_id, "notes": payload.notes},
    )
    return {"shift_id": str(shift_id), "status": "completed", "check_out": timestamp}


# ═══════════════════════════════════════════════════════════
# Employee Portal  (MUST be before /{employee_id} catch-all)
# ═══════════════════════════════════════════════════════════

@api_router.get("/portal/{employee_id}")
def employee_portal(
    request: Request,
    employee_id: str = Path(...),
    prop_id: int | None = Query(default=None, ge=1),
):
    """Return the full portal payload for an employee dashboard.

    Aggregates: employee info, current shift, KPIs from operations,
    weekly roster, payroll hours, and recent activity timeline.
    """
    db = get_database()
    try:
        emp_oid = ObjectId(employee_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")

    emp = db[EMPLOYEES_COLLECTION].find_one({"_id": emp_oid, "is_active": True})
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")

    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    today_end = datetime(now.year, now.month, now.day, 23, 59, 59, 999999, tzinfo=timezone.utc)

    # ── Current Shift ──
    current_shift: dict | None = None
    shift_doc = db[SHIFTS_COLLECTION].find_one({
        "employee_id": employee_id,
        "date": today_str,
        "status": {"$in": ["pending", "active"]},
    })
    if shift_doc:
        current_shift = {
            "id": str(shift_doc.pop("_id")),
            "employee_id": shift_doc.get("employee_id", ""),
            "date": shift_doc.get("date", ""),
            "scheduled_start": shift_doc.get("scheduled_start", ""),
            "scheduled_end": shift_doc.get("scheduled_end", ""),
            "area": shift_doc.get("area", ""),
            "status": shift_doc.get("status", ""),
            "actual_check_in": shift_doc["actual_check_in"].isoformat() if isinstance(shift_doc.get("actual_check_in"), datetime) else None,
            "actual_check_out": shift_doc["actual_check_out"].isoformat() if isinstance(shift_doc.get("actual_check_out"), datetime) else None,
            "notes": shift_doc.get("notes", ""),
            "created_at": shift_doc["created_at"].isoformat() if isinstance(shift_doc.get("created_at"), datetime) else "",
        }

    # ── KPIs from operations ──
    emp_prop_id = emp.get("prop_id")

    payments_today = 0.0
    payments_count = 0
    if emp_prop_id is not None:
        payment_docs = list(db["reservation_payments"].find({
            "prop_id": emp_prop_id,
            "paid_at": {"$gte": today_start, "$lte": today_end},
        }, {"amount": 1}))
        payments_today = round(sum(float(p.get("amount", 0)) for p in payment_docs), 2)
        payments_count = len(payment_docs)

    upsells_today = 0
    if emp_prop_id is not None:
        upsells_today = db["additional_charges"].count_documents({
            "prop_id": emp_prop_id,
            "created_at": {"$gte": today_start, "$lte": today_end},
        })

    kpis = {
        "sales": payments_today,
        "sales_formatted": f"${payments_today:,.2f}",
        "payments": payments_count,
        "upsells": upsells_today,
        "upsells_target": 5,
    }

    # ── Weekly Roster ──
    today_dt = now.date()
    monday = today_dt - timedelta(days=today_dt.weekday())
    day_names = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

    weekly_roster: list[dict] = []
    for i in range(7):
        day_dt = monday + timedelta(days=i)
        date_str = day_dt.strftime("%Y-%m-%d")
        shift = db[SHIFTS_COLLECTION].find_one({
            "employee_id": employee_id,
            "date": date_str,
        })
        entry: dict = {
            "date": date_str,
            "day": day_names[i],
            "day_number": day_dt.day,
            "month": day_dt.month,
            "is_today": date_str == today_str,
            "shift_start": shift.get("scheduled_start", "") if shift else "",
            "shift_end": shift.get("scheduled_end", "") if shift else "",
            "area": shift.get("area", "") if shift else "",
            "status": shift.get("status", "rest") if shift else "rest",
        }
        weekly_roster.append(entry)

    # ── Payroll ──
    month_start_str = today_dt.replace(day=1).strftime("%Y-%m-%d")
    month_shifts = list(db[SHIFTS_COLLECTION].find({
        "employee_id": employee_id,
        "date": {"$gte": month_start_str, "$lte": today_str},
        "status": {"$in": ["active", "completed"]},
    }, {"scheduled_start": 1, "scheduled_end": 1}))

    worked_hours = 0.0
    for s in month_shifts:
        start = s.get("scheduled_start", "")
        end = s.get("scheduled_end", "")
        if start and end:
            try:
                h1, m1 = map(int, start.split(":"))
                h2, m2 = map(int, end.split(":"))
                hours = (h2 - h1) + (m2 - m1) / 60.0
                if hours > 0:
                    worked_hours += hours
            except (ValueError, IndexError):
                pass

    target_hours = 160
    payroll = {
        "worked_hours": round(worked_hours, 1),
        "target_hours": target_hours,
        "progress_pct": min(round(worked_hours / target_hours * 100, 1), 100.0),
        "period_label": today_dt.strftime("%B %Y").upper(),
    }

    # ── Recent Events (Timeline) ──
    recent_events: list[dict] = []

    shift_events = list(db[SHIFTS_COLLECTION].find(
        {"employee_id": employee_id, "status": "completed"},
        {"_id": 0, "date": 1, "actual_check_out": 1, "area": 1},
    ).sort("date", -1).limit(3))

    for se in shift_events:
        check_out = se.get("actual_check_out")
        if isinstance(check_out, datetime):
            check_out = check_out.isoformat()
        recent_events.append({
            "type": "shift_completed",
            "label": "Turno Finalizado",
            "detail": se.get("area", ""),
            "timestamp": check_out or se.get("date", ""),
            "icon": "event_available",
        })

    checkin_shift = db[SHIFTS_COLLECTION].find_one(
        {"employee_id": employee_id, "actual_check_in": {"$ne": None}},
        {"_id": 0, "actual_check_in": 1, "date": 1},
        sort=[("actual_check_in", -1)],
    )
    if checkin_shift:
        cin = checkin_shift.get("actual_check_in")
        if isinstance(cin, datetime):
            cin = cin.isoformat()
        recent_events.insert(0, {
            "type": "check_in",
            "label": "Check-in puntual",
            "detail": f"Fecha: {checkin_shift.get('date', '')}",
            "timestamp": cin or "",
            "icon": "login",
        })

    recent_events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    recent_events = recent_events[:5]

    user = getattr(request.state, "current_user", None) or {}
    register_action(
        prop_id=prop_id or emp_prop_id or 0,
        entity_type="employee_portal",
        entity_id=employee_id,
        action="read",
        summary=f"Consulta de portal de empleado {employee_id}",
        changed_by=user.get("username", "anonymous"),
        metadata={"prop_id": prop_id or emp_prop_id, "url": str(request.url)},
    )
    portal_data = EmployeePortalResponse(
        employee=_enrich_employee(emp),
        current_shift=current_shift,
        kpis=kpis,
        weekly_roster=weekly_roster,
        payroll=payroll,
        recent_events=recent_events,
    )
    return portal_data


# ═══════════════════════════════════════════════════════════
# Employee CRUD  (/{employee_id} MUST be last in its group)
# ═══════════════════════════════════════════════════════════

@api_router.post("", status_code=201)
def create_employee(
    payload: EmployeeCreate = Body(...),
    current_user: dict = Depends(require_login),
):
    """Create a new employee with optional replacement logic."""
    db = get_database()
    now = datetime.now(timezone.utc)

    # Check unique ID document
    existing = db[EMPLOYEES_COLLECTION].find_one({"id_document": payload.id_document})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un empleado con ese documento de identidad",
        )

    doc = {
        "full_name": payload.full_name,
        "id_document": payload.id_document,
        "phone": payload.phone,
        "email": payload.email,
        "address": payload.address,
        "position": payload.position,
        "department": payload.department,
        "hire_date": payload.hire_date,
        "salary": payload.salary,
        "emergency_contact": payload.emergency_contact,
        "emergency_phone": payload.emergency_phone,
        "notes": payload.notes,
        "prop_id": payload.prop_id,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }

    result = db[EMPLOYEES_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id
    enriched = _enrich_employee(doc)

    diff = {
        k: {"old": None, "new": v}
        for k, v in doc.items()
        if k not in ("_id", "created_at", "updated_at") and v is not None
    }
    register_action(
        prop_id=payload.prop_id or 0,
        entity_type="employee",
        entity_id=enriched["id"],
        action="create",
        summary=f"Creación de empleado: {payload.full_name}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )

    # ─── Replacement Logic ───
    if payload.replaces_employee_id:
        try:
            old_id = ObjectId(payload.replaces_employee_id)
            old = db[EMPLOYEES_COLLECTION].find_one({"_id": old_id})
            if old:
                # Mark old employee as inactive
                db[EMPLOYEES_COLLECTION].update_one(
                    {"_id": old_id},
                    {"$set": {"is_active": False, "replaced_by": str(result.inserted_id), "updated_at": now}},
                )
                register_action(
                    prop_id=old.get("prop_id", payload.prop_id or 0),
                    entity_type="employee",
                    entity_id=str(old_id),
                    action="update",
                    summary=f"Reemplazo de empleado: {old.get('full_name', '')} → {payload.full_name}",
                    changed_by=current_user.get("username", "system"),
                    diff={
                        "is_active": {"old": old.get("is_active"), "new": False},
                        "replaced_by": {"old": None, "new": enriched["id"]},
                    },
                )
                # Transfer shifts
                if payload.transfer_shifts:
                    db["employee_shifts"].update_many(
                        {"employee_id": str(old_id)},
                        {"$set": {"employee_id": str(result.inserted_id), "transferred_from": str(old_id)}},
                    )
                # Transfer permissions
                if payload.transfer_permissions:
                    db["employee_permissions"].update_many(
                        {"employee_id": str(old_id)},
                        {"$set": {"employee_id": str(result.inserted_id), "transferred_from": str(old_id)}},
                    )
        except Exception:
            pass  # non-critical: old employee may not exist

    return enriched


@api_router.get("")
def list_employees(
    request: Request,
    search: str | None = Query(default=None),
    department: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    prop_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    from math import ceil
    db = get_database()
    query: dict = {}
    if search:
        query["$or"] = [
            {"full_name": {"$regex": search, "$options": "i"}},
            {"id_document": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
        ]
    if department:
        query["department"] = department
    if is_active is not None:
        query["is_active"] = is_active
    if prop_id is not None:
        query["prop_id"] = prop_id

    total = db[EMPLOYEES_COLLECTION].count_documents(query)
    cursor = (
        db[EMPLOYEES_COLLECTION]
        .find(query)
        .sort("full_name", 1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_enrich_employee(doc) for doc in cursor]

    user = getattr(request.state, "current_user", None) or {}
    register_action(
        prop_id=prop_id or 0,
        entity_type="employee",
        entity_id="list",
        action="read",
        summary=f"Listado de empleados (total={total}, page={page})",
        changed_by=user.get("username", "anonymous"),
        metadata={
            "search": search,
            "department": department,
            "is_active": is_active,
            "prop_id": prop_id,
            "page": page,
            "page_size": page_size,
            "url": str(request.url),
        },
    )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, ceil(total / page_size)) if total else 1,
        "has_next": page * page_size < total,
        "has_prev": page > 1,
    }


@api_router.get("/{employee_id}")
def get_employee(
    request: Request,
    employee_id: str = Path(...),
):
    db = get_database()
    try:
        doc = db[EMPLOYEES_COLLECTION].find_one({"_id": ObjectId(employee_id)})
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")
    user = getattr(request.state, "current_user", None) or {}
    register_action(
        prop_id=doc.get("prop_id", 0),
        entity_type="employee",
        entity_id=employee_id,
        action="read",
        summary=f"Consulta de empleado {doc.get('full_name', employee_id)}",
        changed_by=user.get("username", "anonymous"),
        metadata={"url": str(request.url)},
    )
    return _enrich_employee(doc)


@api_router.put("/{employee_id}")
def update_employee(
    employee_id: str = Path(...),
    payload: EmployeeUpdate = Body(...),
    current_user: dict = Depends(require_login),
):
    db = get_database()
    try:
        oid = ObjectId(employee_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")

    before = db[EMPLOYEES_COLLECTION].find_one({"_id": oid})
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")

    update = {k: v for k, v in payload.model_dump(exclude_none=True).items()}
    if not update:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No hay campos para actualizar")

    update["updated_at"] = datetime.now(timezone.utc)
    db[EMPLOYEES_COLLECTION].update_one({"_id": oid}, {"$set": update})

    doc = db[EMPLOYEES_COLLECTION].find_one({"_id": oid})
    diff = {
        k: {"old": before.get(k), "new": v}
        for k, v in update.items()
        if k != "updated_at" and before.get(k) != v
    }
    register_action(
        prop_id=doc.get("prop_id", 0),
        entity_type="employee",
        entity_id=employee_id,
        action="update",
        summary=f"Actualización de empleado: {doc.get('full_name', employee_id)}",
        changed_by=current_user.get("username", "system"),
        diff=diff if diff else None,
    )
    return _enrich_employee(doc)


@api_router.delete("/{employee_id}", status_code=204)
def delete_employee(
    employee_id: str = Path(...),
    current_user: dict = Depends(require_login),
):
    db = get_database()
    try:
        oid = ObjectId(employee_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")
    before = db[EMPLOYEES_COLLECTION].find_one({"_id": oid})
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")
    result = db[EMPLOYEES_COLLECTION].delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")
    diff = {
        "deleted": {"old": before.get("is_active"), "new": True},
        "full_name": {"old": before.get("full_name"), "new": None},
    }
    register_action(
        prop_id=before.get("prop_id", 0),
        entity_type="employee",
        entity_id=employee_id,
        action="delete",
        summary=f"Eliminación de empleado: {before.get('full_name', employee_id)}",
        changed_by=current_user.get("username", "system"),
        diff=diff,
    )
