"""Business logic for the property-approval queue (Fase 1 del gate).

Design: `docs/APROBACION_HOTELES_Y_PRICING.md` §2-§5. The onboarding
(``register_property.confirm_code``) creates the owner user and the
``dim_hotels`` row in ``pending_approval`` (hotel NOT operational). The super
admin reviews the queue under ``/api/admin/property-registrations`` and, on
approve, this service:

1. Clones the ``gerente_hotel`` global template into a ``hotel_roles`` row
   (reusing ``hotel_permissions.service.create_hotel_role``).
2. Assigns the owner to that role (reusing ``assign_user_to_role``) — the
   owner becomes the hotel admin with ``hotel.manage_roles`` from day 1,
   satisfying the >= 1 active admin invariant.
3. Activates the hotel (``is_operational``/``published``) and the owner.

Ordering matters for atomicity: role clone + assignment happen BEFORE the
activation so a failure leaves the registration untouched (still pending)
instead of an approved hotel without a manager.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.app.core.outbox import enqueue_audit_log
from src.app.modules.hotel_permissions.service import (
    NON_HOTEL_TEMPLATES,
    ConflictError,
    assign_user_to_role,
    create_hotel_role,
)
from src.app.modules.property_approval.notifications import (
    notify_registration_approved,
    notify_registration_changes_requested,
    notify_registration_rejected,
)
from src.app.modules.property_approval.pricing import suggested_band_for

PENDING = "pending_approval"
APPROVED = "approved"
REJECTED = "rejected"
CHANGES_REQUESTED = "changes_requested"

# The canonical manager template cloned on approval (must exist in the
# global ``roles`` catalog as is_template/is_system and NOT be in
# NON_HOTEL_TEMPLATES — it isn't).
GERENTE_TEMPLATE = "gerente_hotel"
GERENTE_DISPLAY_NAME = "Gerente de Hotel"

APPROVAL_ENTITY = "hotel_registration"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _audit_registration(
    db,
    *,
    prop_id: int,
    action: str,
    changed_by: str,
    summary: str,
    diff: dict[str, Any] | None = None,
) -> None:
    """Best-effort audit trail for registration transitions (outbox)."""
    entry: dict[str, Any] = {
        "timestamp": _now(),
        "prop_id": prop_id,
        "entity_type": APPROVAL_ENTITY,
        "entity_id": str(prop_id),
        "action": action,
        "summary": summary,
        "changed_by": changed_by or "system",
    }
    if diff:
        entry["diff"] = diff
    enqueue_audit_log(db, entry)


def _owner_summary(user: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "owner_user_id": str(user["_id"]) if user else "",
        "owner_username": (user or {}).get("username", ""),
        "owner_email": (user or {}).get("email", ""),
        "owner_display_name": (user or {}).get("display_name", ""),
    }


def _registration_summary(hotel: dict[str, Any]) -> dict[str, Any]:
    return {
        "prop_id": hotel.get("prop_id"),
        "hotel_name": hotel.get("hotel_name") or hotel.get("display_name") or "",
        "property_type": hotel.get("property_type", ""),
        "city": hotel.get("city", ""),
        "country_label": hotel.get("display_country_label", ""),
        "currency": hotel.get("currency", ""),
        "total_rooms_declared": hotel.get("total_rooms_declared", 0),
        "approval_status": hotel.get("approval_status", "approved"),
        "submitted_at": hotel.get("created_at"),
        "status_changed_at": hotel.get("approval_status_changed_at"),
        "description": hotel.get("description", ""),
        "contact_phone": hotel.get("contact_phone", ""),
    }


def list_registrations(
    db,
    status: str = PENDING,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """List registrations in the given approval status (default: pending)."""
    query: dict[str, Any] = {}
    if status:
        query["approval_status"] = status
    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or 20), 1), 100)
    cursor = (
        db.dim_hotels.find(query)
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items: list[dict[str, Any]] = []
    for hotel in cursor:
        owner = None
        if hotel.get("owner_user_id"):
            owner = db.users.find_one(
                {"_id": hotel["owner_user_id"]},
                {"username": 1, "email": 1, "display_name": 1},
            )
        items.append({**_registration_summary(hotel), **_owner_summary(owner)})
    return {
        "items": items,
        "total": db.dim_hotels.count_documents(query),
        "status": status or "all",
    }


def get_registration(db, prop_id: int) -> dict[str, Any] | None:
    """Full registration detail (declared data + owner), or None."""
    hotel = db.dim_hotels.find_one({"prop_id": int(prop_id)})
    if not hotel:
        return None
    owner = None
    if hotel.get("owner_user_id"):
        owner = db.users.find_one(
            {"_id": hotel["owner_user_id"]},
            {"username": 1, "email": 1, "display_name": 1},
        )
    return {**_registration_summary(hotel), **_owner_summary(owner)}


def approve_registration(
    db,
    prop_id: int,
    *,
    approver_username: str,
    actor_user_id,
    actor_is_super_admin: bool,
) -> dict[str, Any]:
    """Approve a pending registration: clone role → assign owner → activate.

    Raises:
        KeyError: registration not found (404).
        ConflictError: registration not pending (409).
        ValueError: missing owner or missing/unclonable gerente template (400).
    """
    hotel = db.dim_hotels.find_one({"prop_id": int(prop_id)})
    if not hotel:
        raise KeyError("registration_not_found")
    current_status = hotel.get("approval_status", "approved")
    if current_status != PENDING:
        raise ConflictError(
            f"El registro del hotel {prop_id} no está pendiente de aprobación "
            f"(estado actual: {current_status})."
        )

    owner = None
    if hotel.get("owner_user_id"):
        owner = db.users.find_one({"_id": hotel["owner_user_id"]})
    if not owner:
        raise ValueError("El registro no tiene un usuario dueño válido.")

    template = db.roles.find_one({"role_name": GERENTE_TEMPLATE})
    if (
        not template
        or not (template.get("is_template") or template.get("is_system"))
        or template.get("role_name") in NON_HOTEL_TEMPLATES
    ):
        raise ValueError(
            f"Falta la plantilla base '{GERENTE_TEMPLATE}' para clonar el rol "
            "del gerente al aprobar."
        )

    # Pre-chequeo de pertenencia estricta ANTES de clonar: `assign_user_to_role`
    # lo re-verifica, pero adelantarlo evita el hueco de atomicidad teórico en
    # el que el rol clonado quedaría huérfano si la asignación fallara después
    # (y un reintento del approve chocaría con el nombre duplicado).
    owner_hotels = [int(p) for p in (owner.get("assigned_hotels") or [])]
    if int(prop_id) not in owner_hotels:
        raise ValueError(
            "El dueño del registro no está asignado al hotel (assigned_hotels); "
            "no se puede aprobar."
        )

    # 1) Clonar el rol del gerente (valida los códigos contra el catálogo).
    role = create_hotel_role(
        db,
        int(prop_id),
        name=GERENTE_TEMPLATE,
        display_name=GERENTE_DISPLAY_NAME,
        permissions=[],
        based_on_role_id=str(template["_id"]),
        created_by=approver_username,
    )
    # 2) Asignar al dueño (pertenencia estricta: assigned_hotels ya trae el prop_id).
    try:
        assignment = assign_user_to_role(
            db,
            int(prop_id),
            user_id=str(owner["_id"]),
            role_id=str(role["_id"]),
            assigned_by=approver_username,
            actor_user_id=actor_user_id,
            actor_is_super_admin=actor_is_super_admin,
        )
    except Exception:
        # Red de seguridad: nunca dejar un hotel_role clonado huérfano si la
        # asignación falla — el reintento del approve no debe chocar con el
        # nombre duplicado. El registro sigue pendiente (nada se activó).
        db.hotel_roles.delete_one({"_id": role["_id"]})
        raise
    # 3) Activar (último paso: si 1 o 2 fallan, el registro sigue pendiente).
    now = _now()
    band = suggested_band_for(db, hotel.get("total_rooms_declared", 0)) or {}
    db.dim_hotels.update_one(
        {"_id": hotel["_id"]},
        {
            "$set": {
                "approval_status": APPROVED,
                "approval_status_changed_at": now,
                "is_operational": True,
                "published": True,
                "approved_at": now,
                # Línea 1 del pricing: la banda sugerida se fija al aprobar
                # (el admin puede sobreescribirla después vía price_band_override).
                "price_band": band.get("band"),
                "price_band_label": band.get("label", ""),
                "price_band_monthly_usd": band.get("monthly_usd"),
                "price_band_override": False,
                "updated_at": now,
            }
        },
    )
    db.users.update_one(
        {"_id": owner["_id"]},
        {
            "$set": {
                "approval_status": APPROVED,
                "approval_status_changed_at": now,
                "is_active": True,
                "updated_at": now,
            }
        },
    )

    hotel_name = hotel.get("hotel_name") or hotel.get("display_name") or ""
    _audit_registration(
        db,
        prop_id=int(prop_id),
        action="approved",
        changed_by=approver_username,
        summary=f"Hotel «{hotel_name}» aprobado; rol gerente clonado y dueño asignado.",
        diff={
            "approval_status": {"old": PENDING, "new": APPROVED},
            "hotel_role_id": {"old": None, "new": str(role["_id"])},
            "assignment_id": {"old": None, "new": str(assignment["_id"])},
            "price_band": {"old": None, "new": band.get("band")},
        },
    )

    # UX-2: notificar al dueño (best-effort; la transición ya quedó auditada).
    notify_registration_approved(
        (owner.get("email") or ""),
        hotel_name=hotel_name,
        plan_label=band.get("label", ""),
        monthly_usd=band.get("monthly_usd", 0),
    )

    return {
        "prop_id": int(prop_id),
        "hotel_role_id": str(role["_id"]),
        "assignment_id": str(assignment["_id"]),
        "price_band": band.get("band"),
        "price_band_monthly_usd": band.get("monthly_usd"),
        "message": f"Hotel «{hotel_name}» aprobado y activado.",
    }


def _resolve_registration(db, prop_id: int, allowed: set[str] | None = None) -> dict[str, Any]:
    """Fetch the registration and validate it can transition from its state.

    Raises:
        KeyError: registration not found (404).
        ConflictError: current state cannot transition (409).
    """
    hotel = db.dim_hotels.find_one({"prop_id": int(prop_id)})
    if not hotel:
        raise KeyError("registration_not_found")
    current = hotel.get("approval_status", APPROVED)
    if allowed is not None and current not in allowed:
        raise ConflictError(
            f"El registro del hotel {prop_id} no puede pasar de "
            f"'{current}' a esta acción."
        )
    return hotel


def _registration_owner(db, hotel: dict[str, Any]) -> dict[str, Any]:
    owner = None
    if hotel.get("owner_user_id"):
        owner = db.users.find_one({"_id": hotel["owner_user_id"]})
    if not owner:
        raise ValueError("El registro no tiene un usuario dueño válido.")
    return owner


def reject_registration(
    db,
    prop_id: int,
    *,
    reason: str,
    changed_by: str = "system",
) -> dict[str, Any]:
    """Reject a registration with a mandatory reason (never generic).

    The owner's account stays ACTIVE so they can see the reason once in the
    app (registration-status); the hard deactivation happens lazily after
    REJECTION_GRACE_DAYS (security/approval.py). Sessions stay alive but are
    restricted to the approval allowlist by the middleware.

    Raises:
        KeyError: registration not found (404).
        ConflictError: already approved / terminal (409).
        ValueError: empty reason or missing owner (400).
    """
    clean_reason = (reason or "").strip()
    if not clean_reason:
        raise ValueError("El motivo del rechazo es obligatorio.")

    hotel = _resolve_registration(db, prop_id, allowed={PENDING, CHANGES_REQUESTED})
    owner = _registration_owner(db, hotel)

    now = _now()
    db.dim_hotels.update_one(
        {"_id": hotel["_id"]},
        {
            "$set": {
                "approval_status": REJECTED,
                "approval_status_changed_at": now,
                "rejected_reason": clean_reason,
                "rejected_at": now,
                # Invariante de estado (docs/APROBACION §2/§9): un hotel
                # rechazado es TERMINAL y NUNCA puede quedar visible/operativo
                # — se fuerza published/is_operational en false SIN depender de
                # que el onboarding los haya escrito (el reject solo aplica a
                # pending/changes_requested, pero una regresión futura del
                # onboarding no puede dejar un hotel rechazado publicado).
                "published": False,
                "is_operational": False,
                "updated_at": now,
            }
        },
    )
    db.users.update_one(
        {"_id": owner["_id"]},
        {
            "$set": {
                "approval_status": REJECTED,
                "approval_status_changed_at": now,
                "rejected_reason": clean_reason,
                "rejected_at": now,
                # is_active se apaga SOLO tras la gracia (security/approval.py).
                "updated_at": now,
            }
        },
    )

    hotel_name = hotel.get("hotel_name") or hotel.get("display_name") or ""
    _audit_registration(
        db,
        prop_id=int(prop_id),
        action="rejected",
        changed_by=changed_by,
        summary=f"Hotel «{hotel_name}» rechazado: {clean_reason}",
        diff={
            "approval_status": {"old": hotel.get("approval_status", PENDING), "new": REJECTED},
            "rejected_reason": {"old": None, "new": clean_reason},
            # El flip del invariante queda auditable: en el flujo normal es un
            # no-op (false→false); solo cambia si la fila llegó publicada.
            "published": {"old": hotel.get("published"), "new": False},
            "is_operational": {"old": hotel.get("is_operational"), "new": False},
        },
    )

    notify_registration_rejected(
        (owner.get("email") or ""),
        hotel_name=hotel_name,
        reason=clean_reason,
    )

    return {
        "prop_id": int(prop_id),
        "approval_status": REJECTED,
        "message": f"Hotel «{hotel_name}» rechazado.",
    }


def request_changes_registration(
    db,
    prop_id: int,
    *,
    feedback: str,
    changed_by: str = "system",
) -> dict[str, Any]:
    """Request data corrections from the owner (pending → changes_requested).

    Raises:
        KeyError: registration not found (404).
        ConflictError: already approved (409).
        ValueError: empty feedback or missing owner (400).
    """
    clean_feedback = (feedback or "").strip()
    if not clean_feedback:
        raise ValueError("El feedback de los cambios es obligatorio.")

    hotel = _resolve_registration(db, prop_id, allowed={PENDING, CHANGES_REQUESTED})
    owner = _registration_owner(db, hotel)
    # Asimetría intencional con reject: request-changes NO fuerza
    # published=false — el registro sigue en el embudo de revisión
    # (changes_requested → pending → approve) y debe seguir publicable.
    # El force-unpublish es exclusivo del estado terminal (rejected).

    now = _now()
    db.dim_hotels.update_one(
        {"_id": hotel["_id"]},
        {
            "$set": {
                "approval_status": CHANGES_REQUESTED,
                "approval_status_changed_at": now,
                "feedback": clean_feedback,
                "updated_at": now,
            }
        },
    )
    db.users.update_one(
        {"_id": owner["_id"]},
        {
            "$set": {
                "approval_status": CHANGES_REQUESTED,
                "approval_status_changed_at": now,
                "feedback": clean_feedback,
                "updated_at": now,
            }
        },
    )

    hotel_name = hotel.get("hotel_name") or hotel.get("display_name") or ""
    _audit_registration(
        db,
        prop_id=int(prop_id),
        action="changes_requested",
        changed_by=changed_by,
        summary=f"Cambios solicitados para «{hotel_name}»: {clean_feedback}",
        diff={
            "approval_status": {"old": hotel.get("approval_status", PENDING), "new": CHANGES_REQUESTED},
            "feedback": {"old": None, "new": clean_feedback},
        },
    )

    notify_registration_changes_requested(
        (owner.get("email") or ""),
        hotel_name=hotel_name,
        feedback=clean_feedback,
    )

    return {
        "prop_id": int(prop_id),
        "approval_status": CHANGES_REQUESTED,
        "message": f"Se solicitaron cambios para «{hotel_name}».",
    }
