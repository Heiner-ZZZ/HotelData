from __future__ import annotations

import calendar as _cal
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, Request, status

from passlib.context import CryptContext

from src.database.connection import get_database
from src.app.modules.hr.schemas import (
    DepartmentCreate,
    EmployeeCreate,
    EmployeePortalResponse,
    EmployeeShiftCheckIn,
    EmployeeShiftCheckOut,
    EmployeeShiftCreate,
    EmployeeUpdate,
    ModuleStatus,
)
from src.app.modules.hr.service.collections import (
    DEPARTMENTS_COLLECTION,
    EMPLOYEES_COLLECTION,
    SHIFTS_COLLECTION,
    ensure_hr_collections,
    module_status,
)
from src.app.modules.partner.services.audit import register_action
from src.app.security.dependencies import require_login

_password_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _ensure_user_account(db, employee_doc: dict) -> dict:
    """Auto-generate a user account for an employee if none exists.

    Returns dict with username and (first-time only) generated password.
    """
    user_id = employee_doc.get("user_id")
    if user_id:
        try:
            user = db.users.find_one({"_id": ObjectId(user_id)})
            if user:
                return {"username": user.get("username", ""), "password": None}
        except Exception:
            pass

    import secrets
    email = (employee_doc.get("email") or "").strip().lower()
    name = (employee_doc.get("full_name") or "").strip().lower()
    username = email if email else name.replace(" ", ".")
    if not username:
        oid = employee_doc.get("_id")
        username = f"emp_{str(oid)[-8:] if oid else 'unknown'}"

    if db.users.find_one({"username": username}):
        username = f"{username}_{secrets.token_hex(3)}"

    user_email = email if email else f"{username}@hoteldata.local"
    if db.users.find_one({"email": user_email}):
        user_email = f"{username}_{secrets.token_hex(3)}@hoteldata.local"

    role_map = {
        "recepción": "operador_datos",
        "reception": "operador_datos",
        "limpieza": "operador_datos",
        "housekeeping": "operador_datos",
        "administración": "gerente_hotel",
        "administration": "gerente_hotel",
        "revenue": "revenue_manager",
        "marketing": "marketing_hotelero",
    }
    dept = (employee_doc.get("department") or "").strip().lower()
    role = role_map.get(dept, "operador_datos")

    password = secrets.token_urlsafe(10)
    password_hash = _password_ctx.hash(password)
    now = datetime.now(timezone.utc)

    emp_prop_id = employee_doc.get("prop_id")
    assigned_hotels: list[int] = [emp_prop_id] if emp_prop_id is not None else []

    user_doc = {
        "username": username,
        "email": user_email,
        "password_hash": password_hash,
        "display_name": employee_doc.get("full_name", username),
        "primary_role": role,
        "prop_id": emp_prop_id,
        "assigned_hotels": assigned_hotels,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    result = db.users.insert_one(user_doc)
    user_id_str = str(result.inserted_id)

    db[EMPLOYEES_COLLECTION].update_one(
        {"_id": employee_doc["_id"]},
        {"$set": {"user_id": user_id_str, "updated_at": now}},
    )

    return {"username": username, "password": password}


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
    week_start: str | None = Query(default=None, description="YYYY-MM-DD of the Monday of the week to show. Defaults to current week."),
):
    """Return the full portal payload for an employee dashboard.

    Aggregates: employee info, current shift, KPIs from operations,
    weekly roster (for the given week_start or current week),
    payroll hours, and recent activity timeline.
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
            "id": str(shift_doc.get("_id")),
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

    # ── Weekly Roster (supports week_start navigation) ──
    if week_start:
        try:
            monday_dt = datetime.strptime(week_start, "%Y-%m-%d").date()
            # Ensure it's a Monday; if not, shift to the nearest Monday
            if monday_dt.weekday() != 0:
                monday_dt = monday_dt - timedelta(days=monday_dt.weekday())
        except ValueError:
            monday_dt = now.date() - timedelta(days=now.date().weekday())
    else:
        monday_dt = now.date() - timedelta(days=now.date().weekday())

    day_names = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

    weekly_roster: list[dict] = []
    for i in range(7):
        day_dt = monday_dt + timedelta(days=i)
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
            "actual_check_in": shift["actual_check_in"].isoformat() if shift and isinstance(shift.get("actual_check_in"), datetime) else None,
            "actual_check_out": shift["actual_check_out"].isoformat() if shift and isinstance(shift.get("actual_check_out"), datetime) else None,
        }
        weekly_roster.append(entry)

    # ── Payroll ──
    today_dt = now.date()
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
# Employee Portal — Tasks & Operations
# ═══════════════════════════════════════════════════════════

@api_router.get("/portal/{employee_id}/tasks")
def employee_portal_tasks(
    employee_id: str = Path(...),
    current_user: dict = Depends(require_login),
):
    """Return the employee's assigned tasks, dirty rooms, and daily duties.

    Aggregates from housekeeping_tasks, maintenance_tasks, and room_status_log.
    """
    db = get_database()
    try:
        emp_oid = ObjectId(employee_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")

    emp = db[EMPLOYEES_COLLECTION].find_one({"_id": emp_oid, "is_active": True})
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")

    emp_name = emp.get("full_name", "")
    emp_prop_id = emp.get("prop_id")
    emp_dept = (emp.get("department") or "").strip().lower()

    # ── Assigned housekeeping tasks (not completed/deleted) ──
    hk_query: dict = {
        "assigned_to": {"$regex": emp_name, "$options": "i"},
        "status": {"$nin": ["completed", "deleted"]},
    }
    if emp_prop_id is not None:
        hk_query["prop_id"] = emp_prop_id

    hk_tasks = []
    for doc in db["housekeeping_tasks"].find(hk_query).sort("created_at", -1).limit(20):
        hk_tasks.append({
            "id": str(doc["_id"]),
            "type": "cleaning",
            "room_label": doc.get("room_label", ""),
            "task_type": doc.get("task_type", ""),
            "status": doc.get("status", "pending"),
            "priority": doc.get("priority", "normal"),
            "note": doc.get("note", ""),
            "scheduled_date": doc.get("scheduled_date", ""),
            "created_at": doc["created_at"].isoformat() if isinstance(doc.get("created_at"), datetime) else str(doc.get("created_at", "")),
        })

    # ── Maintenance tasks for the property (not completed/deleted) ──
    mt_tasks = []
    if emp_prop_id is not None:
        mt_query: dict = {
            "prop_id": emp_prop_id,
            "status": {"$nin": ["completed", "deleted"]},
        }
        for doc in db["maintenance_tasks"].find(mt_query).sort("scheduled_date", -1).limit(20):
            mt_tasks.append({
                "id": str(doc["_id"]),
                "type": "maintenance",
                "room_label": doc.get("room_label", ""),
                "title": doc.get("title", ""),
                "task_type": doc.get("task_type", ""),
                "status": doc.get("status", "scheduled"),
                "priority": doc.get("priority", "normal"),
                "scheduled_date": doc.get("scheduled_date", ""),
                "created_at": doc["created_at"].isoformat() if isinstance(doc.get("created_at"), datetime) else str(doc.get("created_at", "")),
            })

    # ── Dirty rooms in the employee's property ──
    dirty_rooms = []
    if emp_prop_id is not None:
        dirty_query: dict = {
            "prop_id": emp_prop_id,
            "status": {"$in": ["vacant_dirty", "occupied_dirty", "dirty"]},
        }
        for doc in db["room_status_log"].find(dirty_query).sort("room_label", 1).limit(20):
            dirty_rooms.append({
                "room_label": doc.get("room_label", ""),
                "room_number": doc.get("room_number", ""),
                "status": doc.get("status", ""),
                "floor": doc.get("floor", ""),
                "note": doc.get("note", ""),
            })

    # ── Daily duties from employee record (with department fallback) ──
    daily_duties = emp.get("daily_duties")
    if not daily_duties or not isinstance(daily_duties, list):
        daily_duties = _default_duties_for_dept(emp_dept)

    register_action(
        prop_id=emp_prop_id or 0,
        entity_type="employee_portal_tasks",
        entity_id=employee_id,
        action="read",
        summary=f"Consulta de tareas del portal de empleado {employee_id}",
        changed_by=current_user.get("username", "system"),
        metadata={"hk_tasks": len(hk_tasks), "mt_tasks": len(mt_tasks), "dirty_rooms": len(dirty_rooms)},
    )

    return {
        "employee_id": employee_id,
        "employee_name": emp_name,
        "assigned_tasks": hk_tasks + mt_tasks,
        "dirty_rooms": dirty_rooms,
        "daily_duties": daily_duties,
    }


# ═══════════════════════════════════════════════════════════
# My Portal (self-service redirect for employees)
# ═══════════════════════════════════════════════════════════

@api_router.get("/my-portal")
def my_portal(current_user: dict = Depends(require_login)):
    """Return the employee portal URL for the currently logged-in user.

    Also syncs assigned_hotels from the employee record to the user document
    so housekeeping / property-aware APIs work correctly.
    """
    db = get_database()
    user_id = str(current_user.get("_id"))
    emp = db[EMPLOYEES_COLLECTION].find_one({"user_id": user_id, "is_active": True}, {"_id": 1, "full_name": 1, "prop_id": 1})
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró un perfil de empleado vinculado a este usuario.")

    # ── Sync assigned_hotels to user doc ──
    emp_prop_id = emp.get("prop_id")
    if emp_prop_id is not None:
        user_assigned = current_user.get("assigned_hotels", [])
        if not user_assigned or emp_prop_id not in user_assigned:
            db.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$addToSet": {"assigned_hotels": emp_prop_id}, "$set": {"updated_at": datetime.now(timezone.utc)}},
            )

    return {
        "employee_id": str(emp["_id"]),
        "full_name": emp.get("full_name", ""),
        "portal_url": f"/management/hr/portal/{str(emp['_id'])}",
    }


# ═══════════════════════════════════════════════════════════
# Attendance History
# ═══════════════════════════════════════════════════════════

@api_router.get("/{employee_id}/attendance")
def employee_attendance(
    employee_id: str = Path(...),
    month: str | None = Query(default=None, description="YYYY-MM format, defaults to current month"),
    current_user: dict = Depends(require_login),
):
    """Return attendance records for an employee in a given month.

    Calculates real hours from actual_check_in → actual_check_out.
    Returns a summary with total days, hours, and punctuality.
    """
    db = get_database()
    try:
        emp_oid = ObjectId(employee_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")

    emp = db[EMPLOYEES_COLLECTION].find_one({"_id": emp_oid, "is_active": True}, {"full_name": 1, "prop_id": 1})
    if not emp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")

    now = datetime.now(timezone.utc)
    today = now.date()

    # Parse month or default to current
    if month and len(month) == 7:
        try:
            year = int(month[:4])
            mon = int(month[5:7])
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de mes inválido. Use YYYY-MM")
    else:
        year = today.year
        mon = today.month

    month_str = f"{year:04d}-{mon:02d}"

    # Calculate month start and end dates
    _, last_day = _cal.monthrange(year, mon)
    month_start_str = f"{year:04d}-{mon:02d}-01"
    month_end_str = f"{year:04d}-{mon:02d}-{last_day:02d}"

    day_names = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

    # Fetch ALL shifts for this employee in the month
    shifts = list(db[SHIFTS_COLLECTION].find({
        "employee_id": employee_id,
        "date": {"$gte": month_start_str, "$lte": month_end_str},
    }).sort("date", 1))

    # Build a lookup by date
    shifts_by_date: dict[str, dict] = {}
    for s in shifts:
        d = s.get("date", "")
        if d not in shifts_by_date:
            shifts_by_date[d] = s

    records: list[dict] = []
    total_worked_seconds = 0.0
    days_worked = 0
    on_time_count = 0
    scheduled_days = 0

    # Iterate all days in the month
    for day_num in range(1, last_day + 1):
        date_str = f"{year:04d}-{mon:02d}-{day_num:02d}"
        day_dt = datetime(year, mon, day_num, tzinfo=timezone.utc)
        day_idx = day_dt.weekday()  # Monday=0
        day_name = day_names[day_idx]

        shift = shifts_by_date.get(date_str)

        if shift:
            check_in = shift.get("actual_check_in")
            check_out = shift.get("actual_check_out")
            sched_start = shift.get("scheduled_start", "")
            sched_end = shift.get("scheduled_end", "")
            status = shift.get("status", "pending")
            area = shift.get("area", "")

            # Calculate real hours
            hours_worked: float | None = None
            if isinstance(check_in, datetime) and isinstance(check_out, datetime):
                delta = check_out - check_in
                hours_worked = round(delta.total_seconds() / 3600, 2)
            elif isinstance(check_in, datetime) and sched_start and sched_end:
                # Has check-in but no check-out — use scheduled end as fallback
                try:
                    hi, mi = map(int, sched_end.split(":"))
                    check_out_fallback = datetime(year, mon, day_num, hi, mi, tzinfo=timezone.utc)
                    delta = check_out_fallback - check_in
                    if delta.total_seconds() > 0:
                        hours_worked = round(delta.total_seconds() / 3600, 2)
                except (ValueError, IndexError):
                    pass

            cin_iso = check_in.isoformat() if isinstance(check_in, datetime) else None
            cout_iso = check_out.isoformat() if isinstance(check_out, datetime) else None

            if hours_worked is not None and hours_worked > 0:
                total_worked_seconds += hours_worked
                days_worked += 1

            # Punctuality: check-in before scheduled_start + 15min grace
            if isinstance(check_in, datetime) and sched_start:
                try:
                    h, m = map(int, sched_start.split(":"))
                    scheduled_dt = datetime(year, mon, day_num, h, m, tzinfo=timezone.utc)
                    grace_dt = scheduled_dt + timedelta(minutes=15)
                    if check_in <= grace_dt:
                        on_time_count += 1
                except (ValueError, IndexError):
                    pass

            if status != "rest":
                scheduled_days += 1

            records.append({
                "date": date_str,
                "day_name": day_name,
                "shift_start": sched_start,
                "shift_end": sched_end,
                "check_in": cin_iso,
                "check_out": cout_iso,
                "hours_worked": hours_worked,
                "status": status,
                "area": area,
            })
        else:
            # No shift scheduled for this day
            records.append({
                "date": date_str,
                "day_name": day_name,
                "shift_start": "",
                "shift_end": "",
                "check_in": None,
                "check_out": None,
                "hours_worked": None,
                "status": "rest",
                "area": "",
            })

    total_hours = round(total_worked_seconds, 1)
    avg_hours = round(total_hours / days_worked, 1) if days_worked else 0
    on_time_pct = round((on_time_count / scheduled_days) * 100, 1) if scheduled_days else 100

    result = {
        "employee_id": employee_id,
        "employee_name": emp.get("full_name", ""),
        "month": month_str,
        "records": records,
        "summary": {
            "total_days": last_day,
            "days_worked": days_worked,
            "total_hours": total_hours,
            "avg_hours_per_day": avg_hours,
            "on_time_percentage": on_time_pct,
            "month": month_str,
        },
    }

    register_action(
        prop_id=emp.get("prop_id", 0),
        entity_type="employee_attendance",
        entity_id=employee_id,
        action="read",
        summary=f"Consulta de historial de asistencias ({month_str})",
        changed_by=current_user.get("username", "system"),
        metadata={"employee_id": employee_id, "month": month_str},
    )
    return result


# ═══════════════════════════════════════════════════════════
# Shift CRUD (schedule management)
# ═══════════════════════════════════════════════════════════

def _default_duties_for_dept(department: str) -> list[dict]:
    """Return default daily duties for a given department. Used as fallback when
    an employee has no custom duties configured."""
    dept = department.strip().lower()
    duties_map: dict[str, list[dict]] = {
        "limpieza": [
            {"label": "Revisar carrito de limpieza", "icon": "shopping_cart", "description": ""},
            {"label": "Cambiar sábanas y toallas", "icon": "bed", "description": ""},
            {"label": "Limpiar baño y reponer amenities", "icon": "shower", "description": ""},
            {"label": "Aspirar y trapear piso", "icon": "mop", "description": ""},
            {"label": "Sacar basura de habitaciones", "icon": "delete", "description": ""},
            {"label": "Reportar daños encontrados", "icon": "report", "description": ""},
        ],
        "housekeeping": [
            {"label": "Revisar carrito de limpieza", "icon": "shopping_cart", "description": ""},
            {"label": "Cambiar sábanas y toallas", "icon": "bed", "description": ""},
            {"label": "Limpiar baño y reponer amenities", "icon": "shower", "description": ""},
            {"label": "Aspirar y trapear piso", "icon": "mop", "description": ""},
            {"label": "Sacar basura de habitaciones", "icon": "delete", "description": ""},
            {"label": "Reportar daños encontrados", "icon": "report", "description": ""},
        ],
        "mantenimiento": [
            {"label": "Revisar reportes de averías", "icon": "plumbing", "description": ""},
            {"label": "Inspeccionar A/C y calefacción", "icon": "ac_unit", "description": ""},
            {"label": "Verificar sistemas eléctricos", "icon": "bolt", "description": ""},
            {"label": "Revisar cerraduras y puertas", "icon": "door_front", "description": ""},
            {"label": "Documentar reparaciones", "icon": "description", "description": ""},
        ],
        "maintenance": [
            {"label": "Revisar reportes de averías", "icon": "plumbing", "description": ""},
            {"label": "Inspeccionar A/C y calefacción", "icon": "ac_unit", "description": ""},
            {"label": "Verificar sistemas eléctricos", "icon": "bolt", "description": ""},
            {"label": "Revisar cerraduras y puertas", "icon": "door_front", "description": ""},
            {"label": "Documentar reparaciones", "icon": "description", "description": ""},
        ],
        "recepción": [
            {"label": "Revisar llegadas y salidas del día", "icon": "event", "description": ""},
            {"label": "Confirmar reservas pendientes", "icon": "confirmation_number", "description": ""},
            {"label": "Atender check-ins programados", "icon": "login", "description": ""},
            {"label": "Gestionar solicitudes de huéspedes", "icon": "support_agent", "description": ""},
            {"label": "Cierre de caja y reporte diario", "icon": "receipt_long", "description": ""},
        ],
        "reception": [
            {"label": "Revisar llegadas y salidas del día", "icon": "event", "description": ""},
            {"label": "Confirmar reservas pendientes", "icon": "confirmation_number", "description": ""},
            {"label": "Atender check-ins programados", "icon": "login", "description": ""},
            {"label": "Gestionar solicitudes de huéspedes", "icon": "support_agent", "description": ""},
            {"label": "Cierre de caja y reporte diario", "icon": "receipt_long", "description": ""},
        ],
    }
    return duties_map.get(dept, [
        {"label": "Revisar asignaciones del día", "icon": "task_alt", "description": ""},
        {"label": "Completar check-in de turno", "icon": "how_to_reg", "description": ""},
        {"label": "Atender solicitudes pendientes", "icon": "pending_actions", "description": ""},
        {"label": "Reportar novedades al supervisor", "icon": "report", "description": ""},
    ])


def _enrich_shift(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    for f in ("created_at", "updated_at"):
        if isinstance(doc.get(f), datetime):
            doc[f] = doc[f].isoformat()
    if isinstance(doc.get("actual_check_in"), datetime):
        doc["actual_check_in"] = doc["actual_check_in"].isoformat()
    if isinstance(doc.get("actual_check_out"), datetime):
        doc["actual_check_out"] = doc["actual_check_out"].isoformat()
    return doc


@api_router.post("/shifts", status_code=201)
def create_shift(
    payload: EmployeeShiftCreate = Body(...),
    current_user: dict = Depends(require_login),
):
    """Create a new shift for an employee."""
    db = get_database()
    now = datetime.now(timezone.utc)

    # Verify employee exists
    try:
        emp_oid = ObjectId(payload.employee_id)
        emp = db[EMPLOYEES_COLLECTION].find_one({"_id": emp_oid}, {"full_name": 1})
        if not emp:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de empleado inválido")

    doc = {
        "employee_id": payload.employee_id,
        "date": payload.date,
        "scheduled_start": payload.scheduled_start,
        "scheduled_end": payload.scheduled_end,
        "area": payload.area,
        "notes": payload.notes,
        "status": "pending",
        "actual_check_in": None,
        "actual_check_out": None,
        "created_at": now,
        "updated_at": now,
    }
    result = db[SHIFTS_COLLECTION].insert_one(doc)
    doc["_id"] = result.inserted_id

    register_action(
        prop_id=emp.get("prop_id", 0),
        entity_type="employee_shift",
        entity_id=str(result.inserted_id),
        action="create",
        summary=f"Turno creado: {emp.get('full_name', '')} - {payload.date} {payload.scheduled_start}-{payload.scheduled_end}",
        changed_by=current_user.get("username", "system"),
        metadata={"employee_id": payload.employee_id, "date": payload.date},
    )
    return _enrich_shift(doc)


@api_router.get("/shifts")
def list_shifts(
    request: Request,
    employee_id: str | None = Query(default=None),
    date: str | None = Query(default=None, description="YYYY-MM-DD"),
    date_from: str | None = Query(default=None, description="YYYY-MM-DD"),
    date_to: str | None = Query(default=None, description="YYYY-MM-DD"),
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(require_login),
):
    """List shifts with optional filters."""
    from math import ceil
    db = get_database()
    query: dict = {}
    if employee_id:
        query["employee_id"] = employee_id
    if date:
        query["date"] = date
    if date_from or date_to:
        date_query: dict = {}
        if date_from:
            date_query["$gte"] = date_from
        if date_to:
            date_query["$lte"] = date_to
        if date_query:
            query["date"] = date_query
    if status_filter:
        query["status"] = status_filter

    total = db[SHIFTS_COLLECTION].count_documents(query)
    cursor = (
        db[SHIFTS_COLLECTION]
        .find(query)
        .sort([("date", 1), ("scheduled_start", 1)])
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [_enrich_shift(doc) for doc in cursor]

    register_action(
        prop_id=0,
        entity_type="employee_shift",
        entity_id="list",
        action="read",
        summary=f"Listado de turnos (total={total})",
        changed_by=current_user.get("username", "system"),
        metadata={"employee_id": employee_id, "date": date, "url": str(request.url)},
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


@api_router.put("/shifts/{shift_id}")
def update_shift(
    shift_id: str = Path(...),
    payload: EmployeeShiftCreate = Body(...),
    current_user: dict = Depends(require_login),
):
    """Update a shift."""
    db = get_database()
    try:
        oid = ObjectId(shift_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno no encontrado")

    before = db[SHIFTS_COLLECTION].find_one({"_id": oid})
    if not before:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno no encontrado")

    now = datetime.now(timezone.utc)
    update = {
        "employee_id": payload.employee_id,
        "date": payload.date,
        "scheduled_start": payload.scheduled_start,
        "scheduled_end": payload.scheduled_end,
        "area": payload.area,
        "notes": payload.notes,
        "updated_at": now,
    }
    db[SHIFTS_COLLECTION].update_one({"_id": oid}, {"$set": update})

    diff = {
        k: {"old": before.get(k), "new": v}
        for k, v in update.items() if k != "updated_at" and before.get(k) != v
    }
    register_action(
        prop_id=0,
        entity_type="employee_shift",
        entity_id=shift_id,
        action="update",
        summary=f"Turno actualizado: {payload.date}",
        changed_by=current_user.get("username", "system"),
        diff=diff if diff else None,
    )
    return _enrich_shift(db[SHIFTS_COLLECTION].find_one({"_id": oid}))


@api_router.delete("/shifts/{shift_id}", status_code=204)
def delete_shift(
    shift_id: str = Path(...),
    current_user: dict = Depends(require_login),
):
    """Delete a shift."""
    db = get_database()
    try:
        oid = ObjectId(shift_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno no encontrado")
    result = db[SHIFTS_COLLECTION].delete_one({"_id": oid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turno no encontrado")
    register_action(
        prop_id=0,
        entity_type="employee_shift",
        entity_id=shift_id,
        action="delete",
        summary=f"Turno eliminado: {shift_id}",
        changed_by=current_user.get("username", "system"),
    )


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
        "user_id": payload.user_id,
        "daily_duties": payload.daily_duties if payload.daily_duties is not None else _default_duties_for_dept(payload.department),
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
    current_user: dict = Depends(require_login),
):
    db = get_database()
    try:
        oid = ObjectId(employee_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")
    doc = db[EMPLOYEES_COLLECTION].find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empleado no encontrado")

    # Auto-generate user account if missing
    creds = _ensure_user_account(db, doc)
    # Re-fetch to get updated user_id
    doc = db[EMPLOYEES_COLLECTION].find_one({"_id": oid})

    enriched = _enrich_employee(doc)
    enriched["username"] = creds["username"]
    enriched["password"] = creds["password"]

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
    return enriched


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
