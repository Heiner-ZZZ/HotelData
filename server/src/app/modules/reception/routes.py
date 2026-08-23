from __future__ import annotations

import logging
from fastapi import APIRouter, Body, Depends, HTTPException, Query

from src.app.security.dependencies import require_permission, require_prop_permission
from src.app.security.permissions import user_has_permission
from src.app.modules.partner.services.audit import register_action
from src.database.connection import get_database

from .shifts import (
    ActiveShiftExistsError,
    ScheduleMismatchError,
    resolve_expected_shift_type as resolve_expected_shift_type,
    _now_dt,
    open_shift,
    close_shift,
    get_active_shift,
    get_shift,
    get_shift_config,
    get_shift_labels,
    list_open_shifts_overview,
    list_shifts,
    list_shifts_for_cash_control,
    upsert_shift_config,
)

logger = logging.getLogger(__name__)

api_router = APIRouter(prefix="/api/reception", tags=["reception-api"])


def _user_owns_shift(shift: dict, user: dict) -> bool:
    """True cuando el turno fue abierto por ``user`` (por ``opened_by_id``
    FK; fallback por ``opened_by`` username para turnos legacy / system)."""
    opened_by_id = shift.get("opened_by_id")
    user_id = user.get("_id")
    if opened_by_id is not None and user_id is not None:
        return str(opened_by_id) == str(user_id)
    return str(shift.get("opened_by") or "") == str(user.get("username") or "")


def _can_view_all_shifts(db, user: dict) -> bool:
    """Gerencia (``shifts.manage``) ve y cierra cualquier turno."""
    return user_has_permission(db, user, "shifts.manage")


def _shift_owner_recorded(shift: dict) -> bool:
    """True cuando el turno lleva dueño (``opened_by`` o ``opened_by_id``)."""
    return bool(shift.get("opened_by")) or shift.get("opened_by_id") is not None


def _shift_visible_to(shift: dict, user: dict, db) -> bool:
    """Gerencia ve todo; el dueño ve su turno; un turno legacy SIN dueño
    registrado queda visible a todos (no hay a quién aislar)."""
    if _can_view_all_shifts(db, user):
        return True
    if not _shift_owner_recorded(shift):
        return True
    return _user_owns_shift(shift, user)


# Cuándo el turno activo pertenece a OTRO empleado, la respuesta no filtra
# datos del turno ajeno (caja/transacciones): solo la señal ``occupied`` + quién
# lo abrió + cuándo alcanza su límite de apertura (para que el empleado sepa
# cuándo podría quedar libre, sin ver los números del compañero).
def _occupied_response(labels: dict, shift: dict) -> dict:
    return {
        "shift": None,
        "shift_type_labels": labels,
        "occupied": True,
        "opener_username": shift.get("opened_by"),
        "opener_employee": shift.get("employee"),
        "expires_at": shift.get("expires_at"),
        "max_open_hours": shift.get("max_open_hours"),
    }


@api_router.get("/shifts/active")
def shift_active_api(
    prop_id: int = Query(..., ge=1),
    current_user: dict = Depends(require_prop_permission("shifts.read")),
):
    """Return the currently active shift for a property, or null.

    ``shift_type_labels`` reflects the property's configured windows so
    the frontend renders the correct labels for the open-shift form.
    """
    shift = get_active_shift(prop_id)
    labels = get_shift_labels(prop_id)
    if shift is None:
        return {"shift": None, "shift_type_labels": labels}
    db = get_database()
    if not _shift_visible_to(shift, current_user, db):
        return _occupied_response(labels, shift)
    return {"shift": shift, "shift_type_labels": labels}


@api_router.post("/shifts/open")
def shift_open_api(
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    payload: dict = Body(...),
    current_user: dict = Depends(require_prop_permission("shifts.create")),
):
    """Open a new reception shift.

    If ``cash_initial`` is omitted, the system carries over the
    ``cash_left`` from the previous closed shift for the same property.

    If another shift is already active for the same property, returns
    HTTP 409 with the active shift snapshot so the frontend can show a
    confirmation modal. The client must either close the previous shift
    manually first, or call back with ``force=true`` to auto-close it
    (use sparingly — force-close discards reconciliation data).
    """
    prop_id = payload.get("prop_id")
    # E 2026-08: el gate por-hotel valida el QUERY prop_id; el body debe
    # coincidir — una llamada inconsistente es sospechosa (400).
    if query_prop_id is not None and int(str(prop_id)) != query_prop_id:
        raise HTTPException(status_code=400, detail="prop_id del query y del body no coinciden")
    shift_type = payload.get("shift_type", "morning")
    employee = payload.get("employee", "")
    raw_cash_initial = payload.get("cash_initial")
    cash_initial = float(raw_cash_initial) if raw_cash_initial is not None else None
    force = bool(payload.get("force", False))
    bypass_schedule_check = bool(payload.get("bypass_schedule_check", False))
    # ``force=true`` originally meant "ignore conflicts to open"; we extend
    # that semantics to also implicitly bypass the schedule check so a
    # legacy caller doesn't trip on a 422 just because the legacy intent
    # (force everything) wasn't expressed as two flags. ``bypass_schedule_check``
    # alone stays available for the gerente-only-override flow without ``force``.
    implicit_bypass_via_force = force and not bypass_schedule_check
    effective_bypass = bypass_schedule_check or force

    if not prop_id:
        raise HTTPException(status_code=400, detail="prop_id es requerido")
    if not employee:
        raise HTTPException(status_code=400, detail="employee es requerido")
    if shift_type not in ("morning", "afternoon", "evening"):
        raise HTTPException(status_code=400, detail="shift_type debe ser: morning, afternoon, evening")

    # Server-controlled identity for audit. Never trust client-side opened_by;
    # we always derive it from the authenticated session.
    opened_by = current_user.get("username") or "system"

    # ── Schedule-bypass permission gate ────────────────────────────────
    # Only gerente_hotel / super_admin (i.e. ``shifts.manage``) may flip
    # ``bypass_schedule_check`` to True; we also accept ``force=true`` as
    # an implicit bypass (legacy callers). We MUST re-check server-side —
    # a frontend disabling of the checkbox is just a UI nicety; an
    # attacker can curl this endpoint directly.
    if effective_bypass:
        db_perm = get_database()
        if not user_has_permission(db_perm, current_user, "shifts.manage"):
            logger.warning(
                "SCHEDULE BYPASS REJECTED — user=%s lacks shifts.manage (prop_id=%s shift_type=%s force=%s bypass=%s)",
                opened_by, prop_id, shift_type, force, bypass_schedule_check,
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "schedule_bypass_forbidden",
                    "message": (
                        "Bypass del horario requiere permiso 'shifts.manage'. "
                        "Pide a un gerente que autorice esta apertura."
                    ),
                    "bypass_requires": "shifts.manage",
                },
            )
        logger.warning(
            "SCHEDULE BYPASS GRANTED — user=%s prop_id=%s shift_type=%s "
            "(force=%s explicit_bypass=%s implicit_via_force=%s)",
            opened_by, prop_id, shift_type, force, bypass_schedule_check, implicit_bypass_via_force,
        )
        # ── Audit-log entry ONLY when a real mismatch WOULD have been rejected ──
        # force=true at the correct hour would otherwise pollute the audit
        # collection with phantom ``implicit_via_force`` rows that aren't
        # actually overrides — gate the row to real mismatches only.
        # ENTIRE branch is best-effort — a Mongo blip during HR lookup OR
        # during register_action MUST NOT surface a 500 here; the bypass
        # gate has already authorized the request, the shift open is
        # about to succeed, so the audit row is purely advisory.
        try:
            audit_at = _now_dt()
            audit_expected, audit_source = resolve_expected_shift_type(opened_by, audit_at, prop_id=prop_id)
            audit_real_mismatch = (audit_expected != shift_type)
            if audit_real_mismatch:
                register_action(
                    prop_id=prop_id,
                    entity_type="shift_schedule",
                    entity_id=f"schedule-bypass:{prop_id}",
                    action="bypass",
                    summary=(
                        f"Schedule bypass: opener={opened_by}, requested={shift_type}, "
                        f"expected={audit_expected} ({audit_source}), prop_id={prop_id}, "
                        f"origin={'explicit_flag' if bypass_schedule_check else 'implicit_via_force'}"
                    ),
                    changed_by=opened_by,
                    diff={
                        "bypassed_check": True,
                        "requested_shift_type": shift_type,
                        "expected_shift_type": audit_expected,
                        "expected_source": audit_source,
                        "origin": "explicit_flag" if bypass_schedule_check else "implicit_via_force",
                        "force": force,
                    },
                )
            else:
                logger.info(
                    "schedule-bypass audit SKIPPED — no actual mismatch "
                    "(opener=%s requested=%s expected=%s force=%s)",
                    opened_by, shift_type, audit_expected, force,
                )
        except Exception:
            logger.exception("Audit enrichment/write failed for schedule bypass; request still proceeds")

    if force:
        logger.info(
            "shift_open called with force=True by user=%s (prop_id=%s, shift_type=%s)",
            opened_by, prop_id, shift_type,
        )

    try:
        result = open_shift(
            prop_id=prop_id,
            shift_type=shift_type,
            employee=employee,
            cash_initial=cash_initial,
            force=force,
            bypass_schedule_check=effective_bypass,
            opened_by=opened_by,
        )
        # ── Audit-log entry on EVERY successful open ──
        # ``reception_shifts`` carries ``opened_by`` but the ``audit_log``
        # collection (feeds /audit + SIEM + SystemPanel) was previously only
        # written on schedule bypass. Now every open surfaces in the audit
        # panel with both the receptionist-typed visual label (``employee``)
        # and the canonical opener (``opened_by`` = current_user.username).
        try:
            opener_display = (
                current_user.get("display_name")
                or current_user.get("full_name")
                or opened_by
            )
            register_action(
                prop_id=prop_id,
                entity_type="reception_shifts",  # plural to match codebase convention (housekeeping_charges, etc.)
                entity_id=f"open:{result['id']}",
                action="open",
                summary=(
                    f"Shift opened: prop_id={prop_id} type={shift_type} "
                    f"employee_label={employee} opened_by={opened_by} "
                    f"({opener_display}) cash_initial={cash_initial}"
                ),
                changed_by=opened_by,
                diff={
                    "prop_id": prop_id,
                    "shift_type": shift_type,
                    "employee_label": employee,
                    "opened_by": opened_by,
                    "opened_by_display": opener_display,
                    "employee_id": result.get("employee_id"),
                    "opened_by_id": result.get("opened_by_id"),
                    "cash_initial": cash_initial,
                    "force": force,
                    "bypass_schedule_check": bypass_schedule_check,
                    "effective_bypass": effective_bypass,
                },
            )
        except Exception:
            logger.exception("Audit write failed for shift open; shift itself is persisted")
        return {
            "shift": result,
            "message": f"Turno {get_shift_labels(prop_id).get(shift_type, shift_type)} abierto",
        }
    except ScheduleMismatchError as exc:
        # 422 Unprocessable Entity — the request was syntactically valid
        # but the schedule validation failed. The frontend reads
        # ``detail.expected`` / ``detail.expected_window`` / ``detail.opener_can_override``
        # to render the override modal (when permitted).
        db_perm = get_database()
        opener_can_override = user_has_permission(db_perm, current_user, "shifts.manage")
        raise HTTPException(
            status_code=422,
            detail={
                "error": "schedule_mismatch",
                "requested": exc.requested,
                "expected": exc.expected,
                "expected_window": exc.expected_window,
                "source": exc.source,
                "now_utc": exc.now_local.isoformat(),
                "opener": exc.opener_username,
                "message": (
                    f"El bloque horario actual es {exc.expected} "
                    f"({exc.expected_window}). Solicitaste turno {exc.requested}."
                ),
                "bypass_requires": "shifts.manage",
                "opener_can_override": opener_can_override,
            },
        ) from exc
    except ActiveShiftExistsError as exc:
        # 409 Conflict — another shift is open. Frontend reads detail.active_shift
        # to populate its confirmation modal. Si el turno activo pertenece a OTRO
        # empleado, se redacta el snapshot (no se filtra caja/transacciones ajenas).
        db_scoped = get_database()
        redacted = not _shift_visible_to(exc.active_shift or {}, current_user, db_scoped)
        raise HTTPException(
            status_code=409,
            detail={
                "error": "active_shift_exists",
                "message": (
                    "Ya hay un turno activo abierto por otro empleado. "
                    "Espera a que se cierre para abrir el tuyo."
                    if redacted
                    else (
                        "Ya hay un turno activo para esta propiedad. Ciérrelo primero "
                        "manualmente o reintente con force=true (no recomendado)."
                    )
                ),
                "active_shift": None if redacted else exc.active_shift,
                "transactions_count": None if redacted else exc.transactions_count,
                "total_collected": None if redacted else exc.total_collected,
                # None => no previous closed shift or over/short not set.
                # 0    => previous closed shift balanced perfectly.
                # ±X   => previous closed shift had a discrepancy of X.
                "last_closed_over_short": exc.last_closed_over_short,
                "force_blocked_by_over_short": (
                    exc.last_closed_over_short is not None
                    and abs(exc.last_closed_over_short) > 0
                ),
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@api_router.get("/shifts/config")
def shift_config_get_api(
    prop_id: int = Query(..., ge=1),
    current_user: dict = Depends(require_prop_permission("shifts.read")),
):
    """Return the effective shift-window config for a property.

    Falls back to the canonical defaults when no custom config exists.
    """
    return {"config": get_shift_config(prop_id)}


@api_router.put("/shifts/config")
def shift_config_put_api(
    query_prop_id: int | None = Query(default=None, ge=1, alias="prop_id"),
    payload: dict = Body(...),
    current_user: dict = Depends(require_prop_permission("shifts.manage")),
):
    """Persist custom cash-shift windows (start/end HH:MM) for a property.

    Body: ``{"prop_id": 1, "windows": {"morning": {"start": "08:00", "end": "16:00"}, ...}}``.
    Validation rejects overlapping / malformed / zero-length windows.
    """
    prop_id = payload.get("prop_id")
    # E 2026-08: el gate por-hotel valida el QUERY prop_id; el body debe
    # coincidir — una llamada inconsistente es sospechosa (400).
    if query_prop_id is not None and int(str(prop_id)) != query_prop_id:
        raise HTTPException(status_code=400, detail="prop_id del query y del body no coinciden")
    windows = payload.get("windows")
    raw_max_open_hours = payload.get("max_open_hours")
    raw_notify_manager_hours = payload.get("notify_manager_hours")
    if not prop_id:
        raise HTTPException(status_code=400, detail="prop_id es requerido")
    if not isinstance(windows, dict):
        raise HTTPException(status_code=400, detail="windows debe ser un objeto con las 3 ventanas")
    max_open_hours = float(raw_max_open_hours) if raw_max_open_hours is not None else None
    notify_manager_hours = float(raw_notify_manager_hours) if raw_notify_manager_hours is not None else None
    username = current_user.get("username") or "system"
    try:
        config = upsert_shift_config(
            prop_id,
            windows,
            max_open_hours=max_open_hours,
            notify_manager_hours=notify_manager_hours,
            updated_by=username,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        register_action(
            prop_id=prop_id,
            entity_type="reception_shift_config",
            entity_id=f"config:{prop_id}",
            action="update",
            summary=(
                f"Ventanas de turno actualizadas para prop_id={prop_id}: "
                f"{config['windows']} (max_open_hours={config['max_open_hours']})"
            ),
            changed_by=username,
            diff={
                "windows": config["windows"],
                "max_open_hours": config["max_open_hours"],
                "is_custom": config["is_custom"],
            },
        )
    except Exception:
        logger.exception("Audit write failed for shift config update; config itself is persisted")
    return {"config": config, "message": "Ventanas de turno actualizadas"}


@api_router.post("/shifts/{shift_id}/close")
def shift_close_api(
    shift_id: str,
    prop_id: int | None = Query(default=None, ge=1),
    payload: dict = Body(default={}),
    current_user: dict = Depends(require_prop_permission("shifts.update")),
):
    """Close an active shift with full cash register data.

    Payload fields:
        - cash_counted: physical cash counted in the drawer (required)
        - cash_left: cash left in drawer for next shift (optional)
        - deposits: list of deposit/drop records
        - closing_notes: free-text observations
        - emergency: true to perform a manager-only emergency close of an
          expired shift (simplified arqueo). Requires ``shifts.manage``.
        - emergency_reason: why the shift needed an emergency close
          (defaults to ``vencimiento``).
    """
    cash_counted = float(payload.get("cash_counted", 0) or 0)
    cash_left = payload.get("cash_left")
    if cash_left is not None:
        cash_left = float(cash_left)
    # Server-controlled identity for audit. NEVER trust payload's closed_by:
    # receptionista could otherwise close "a nombre de" otra persona.
    closed_by = current_user.get("username") or "system"
    deposits = payload.get("deposits") or None
    closing_notes = payload.get("closing_notes", "")
    emergency = bool(payload.get("emergency", False))
    emergency_reason = str(payload.get("emergency_reason", "") or "")

    # Emergency close is a manager power: it bypasses the full-arqueo
    # expectation and unblocks an expired shift. Only ``shifts.manage``
    # (gerente_hotel / super_admin) may use it.
    db_perm = get_database()
    if emergency and not user_has_permission(db_perm, current_user, "shifts.manage", prop_id=prop_id):
        raise HTTPException(
            status_code=403,
            detail="Permiso requerido: shifts.manage — el cierre de emergencia es solo para gerencia",
        )

    # Solo quien abrió el turno (o gerencia) puede cerrarlo: evita que un
    # compañero del mismo hotel arqueé/cierre el cajón de otro empleado.
    target_shift = get_shift(shift_id)
    if target_shift is None:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    # Cross-hotel (E 2026-08): el turno debe pertenecer al hotel pedido.
    if prop_id is not None and target_shift.get("prop_id") != prop_id:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    if not _shift_visible_to(target_shift, current_user, db_perm):
        raise HTTPException(
            status_code=403,
            detail="Solo quien abrió el turno (o un gerente) puede cerrarlo.",
        )

    try:
        result = close_shift(
            shift_id=shift_id,
            cash_counted=cash_counted,
            cash_left=cash_left,
            deposits=deposits,
            closing_notes=closing_notes,
            closed_by=closed_by,
            emergency=emergency,
            emergency_reason=emergency_reason,
        )
        # Audit every close (normal and emergency). The emergency reason
        # travels in the diff so the audit panel / SIEM can show WHY a
        # simplified arqueo was performed (e.g. ``vencimiento``).
        try:
            register_action(
                prop_id=result.get("prop_id") or 0,
                entity_type="reception_shifts",  # plural to match codebase convention
                entity_id=f"close:{shift_id}",
                action="close",
                summary=(
                    f"Shift closed: id={shift_id} by={closed_by} "
                    f"mode={'emergency' if emergency else 'regular'} "
                    f"cash_counted={cash_counted} over_short={result.get('cash_over_short', 0)}"
                    + (f" reason={emergency_reason or 'vencimiento'}" if emergency else "")
                ),
                changed_by=closed_by,
                diff={
                    "shift_id": shift_id,
                    "prop_id": result.get("prop_id") or 0,
                    "close_mode": "emergency" if emergency else "regular",
                    "emergency_reason": (emergency_reason or "vencimiento") if emergency else None,
                    "closed_by": closed_by,
                    "cash_counted": cash_counted,
                    "cash_over_short": result.get("cash_over_short", 0),
                    "total_collected": result.get("total_collected", 0),
                },
            )
        except Exception:  # advisory — the close already succeeded
            logger.exception("close audit row failed for shift_id=%s", shift_id)
        pbreak = result.get("payment_breakdown", {})
        return {
            "shift": result,
            "message": "Turno cerrado",
            "summary": {
                "cash_initial": result.get("cash_initial", 0),
                "cash_final": result.get("cash_final", 0),
                "cash_counted": result.get("cash_counted", 0),
                "cash_left": result.get("cash_left", 0),
                "cash_expected": result.get("cash_expected", 0),
                "cash_over_short": result.get("cash_over_short", 0),
                "total_collected": result.get("total_collected", 0),
                "cash_difference": result.get("cash_difference", 0),
                "transaction_count": len(result.get("transactions", [])),
                "payment_breakdown": {
                    "cash": pbreak.get("cash", 0),
                    "card": pbreak.get("card", 0),
                    "transfer": pbreak.get("transfer", 0),
                    "other": pbreak.get("other", 0),
                    "total": pbreak.get("total", 0),
                },
                "deposit_total": result.get("deposit_total", 0),
                "closing_notes": result.get("closing_notes", ""),
                "payment_count": len(result.get("payment_ids", [])),
                "folio_count": len(result.get("folio_ids", [])),
                "booking_count": len(result.get("booking_ids", [])),
            },
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@api_router.get("/shifts/manager-control")
def shift_manager_control_api(
    prop_id: int | None = Query(default=None, ge=1),
    start_date: str | None = Query(default=None, alias="start_date"),
    end_date: str | None = Query(default=None, alias="end_date"),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(require_permission("shifts.manage")),
):
    """Manager cash-control view: closed shifts with over/short details."""
    shifts = list_shifts_for_cash_control(
        prop_id=prop_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
    )
    return {"items": shifts, "total": len(shifts)}


@api_router.get("/shifts/open-overview")
def shift_open_overview_api(
    current_user: dict = Depends(require_permission("shifts.manage")),
):
    """Management view: EVERY open cash shift across all hotels.

    Each row carries the hotel label, age in hours, the per-hotel
    max-open-hours limit and expiry status — gerencia uses it to spot
    forgotten shifts that are silently blocking front-desk cash ops.
    """
    items = list_open_shifts_overview()
    return {"items": items, "total": len(items)}


@api_router.get("/shifts/{shift_id}")
def shift_detail_api(
    shift_id: str,
    prop_id: int | None = Query(default=None, ge=1),
    current_user: dict = Depends(require_prop_permission("shifts.read")),
):
    """Return detailed info for a specific shift."""
    shift = get_shift(shift_id)
    if shift is None:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    # Cross-hotel (E 2026-08): el turno debe pertenecer al hotel pedido.
    if prop_id is not None and shift.get("prop_id") != prop_id:
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    db = get_database()
    if not _shift_visible_to(shift, current_user, db):
        raise HTTPException(status_code=404, detail="Turno no encontrado")
    return {"shift": shift}


@api_router.get("/shifts")
def shift_list_api(
    prop_id: int | None = Query(default=None, ge=1),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: dict = Depends(require_prop_permission("shifts.read")),
):
    """List shifts for a property, newest first.

    Un empleado solo ve SUS turnos; gerencia (``shifts.manage``) ve todos.
    """
    shifts = list_shifts(prop_id=prop_id, status_filter=status_filter, limit=limit)
    db = get_database()
    if not _can_view_all_shifts(db, current_user):
        shifts = [s for s in shifts if _shift_visible_to(s, current_user, db)]
    return {"items": shifts, "total": len(shifts)}
