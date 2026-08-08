"""Business logic for the Fase 2 per-hotel permissions API.

Collection docs are returned raw (Mongo-native types); the routes layer
owns the wire shape via Pydantic ``*Response`` models (see ``routes.py``).

Guardrails enforced here:
- permission codes validated against the ``permissions`` catalog, plus
  ``ensure_read_dependencies`` (create/update/manage require the resource.read).
- ``(prop_id, name)`` uniqueness for hotel_roles (unique index + DuplicateKeyError → 409).
- hotel_roles and role_assignments are scoped to ``prop_id`` (404 if not).
- cannot delete a hotel_role that still has assignments (409).
- anti self-lockout (the actor is the user resolved by
  ``require_prop_permission("hotel.manage_roles")``): the hotel admin cannot
  edit/delete the hotel_role they are assigned to, cannot change/delete their
  own assignment, and cannot self-assign — always via another admin or
  super_admin. ``super_admin`` keeps a global override (``actor_is_super_admin``).
  Every mutation REQUIRES ``actor_user_id`` (ValueError otherwise, except for
  super_admin): a missing actor would silently disable the guard.
  Known limit: ``delete_hotel_role`` has no anti-lockout for roles with zero
  assignments — a super_admin may delete the last manage-granting role and the
  hotel must recreate it via POST (the >= 1 admin invariant is about
  assignments, not role existence).
- clone templates: only ``is_template``/``is_system`` global roles OUTSIDE
  ``NON_HOTEL_TEMPLATES`` are clonable (creating from ``super_admin`` etc. → 400).
- anti-lockout: the hotel must always keep >= 1 ACTIVE admin
  (a user whose assignment points to an active hotel_role granting
  ``hotel.manage_roles``). Deactivating a role, removing the manage
  permission, or unassigning the last admin → 409. With self-protection the
  hotel-admin path can no longer violate this (the actor is always an admin),
  so the check now mainly guards the super_admin override path.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError

from src.app.core.outbox import enqueue_audit_log
from src.app.modules.hotel_permissions.notifications import (
    notify_role_permissions_changed,
)
from src.app.security.permissions import ensure_read_dependencies

HOTEL_MANAGE_ROLES = "hotel.manage_roles"

# Global roles that must NOT be exposed as clone templates to hotel admins
# (system-only or customer-facing).
NON_HOTEL_TEMPLATES = {
    "super_admin",
    "admin_sistema",
    "cliente",
    "operador_datos",
    "auditor_datos",
}

# Anti self-lockout messages (409). All include the marker "self-lockout" so
# the UI can distinguish them from plain anti-lockout (invariant) errors.
SELF_ROLE_MSG = (
    "No puedes modificar el rol que tienes asignado en este hotel "
    "(protección anti self-lockout). Designa a otro admin o hazlo desde super_admin."
)
OWN_ASSIGNMENT_UPDATE_MSG = (
    "No puedes modificar tu propia asignación de rol en este hotel "
    "(protección anti self-lockout)."
)
OWN_ASSIGNMENT_DELETE_MSG = (
    "No puedes desasignarte a ti mismo en este hotel "
    "(protección anti self-lockout)."
)
SELF_ASSIGN_MSG = (
    "No puedes asignarte un rol a ti mismo en este hotel "
    "(protección anti self-lockout)."
)
SYSTEM_TEMPLATE_MSG = (
    "No puedes clonar roles de solo sistema "
    "(super_admin, admin_sistema, cliente) como plantilla."
)
ACTOR_REQUIRED_MSG = (
    "Contexto del actor requerido (anti self-lockout): toda mutación debe "
    "identificar quién actúa (actor_user_id)."
)


def _ensure_actor_ctx(actor_user_id, actor_is_super_admin: bool) -> None:
    """Contract: every mutation must know its actor.

    The self-protection rule (rule 1) can only be enforced when we know who
    is acting. A future caller that forgets to pass ``actor_user_id`` would
    silently disable the guard — so we fail loud instead (ValueError → 400)
    for non-super-admin actors. ``super_admin`` may omit it (override path).
    """
    if not actor_is_super_admin and actor_user_id is None:
        raise ValueError(ACTOR_REQUIRED_MSG)


class ConflictError(Exception):
    """Business conflict (duplicate, state constraint) → HTTP 409."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _audit_role(
    db,
    *,
    prop_id: int,
    role_id: ObjectId,
    action: str,
    changed_by: str,
    summary: str = "",
    diff: dict[str, Any] | None = None,
) -> None:
    """Best-effort audit trail for ``hotel_role`` mutations.

    Writes one ``audit_log`` row (entity_type="hotel_role",
    entity_id=str(role_id)) through the transactional outbox
    (``enqueue_audit_log``): persisted synchronously when Mongo is healthy,
    retried by the drainer otherwise — never blocks the user-facing request.
    """
    entry: dict[str, Any] = {
        "timestamp": _now(),
        "prop_id": prop_id,
        "entity_type": "hotel_role",
        "entity_id": str(role_id),
        "action": action,
        "summary": summary,
        "changed_by": changed_by or "system",
    }
    if diff:
        entry["diff"] = diff
    enqueue_audit_log(db, entry)


def _available_codes(db) -> set[str]:
    return {
        p["permission_code"]
        for p in db.permissions.find({}, {"permission_code": 1})
    }


def _validate_permissions(db, requested: list[str]) -> list[str]:
    """Normalize a permission list against the catalog (raise ValueError)."""
    available = _available_codes(db)
    unknown = [c for c in requested if c not in available]
    if unknown:
        raise ValueError(
            f"Permisos desconocidos: {', '.join(sorted(unknown))}. "
            f"Deben existir en el catálogo."
        )
    normalized = ensure_read_dependencies(set(requested), available)
    return sorted(c for c in normalized if c in available)


def _template_lookup(db) -> dict[ObjectId, dict[str, Any]]:
    """Global roles usable as clone templates (is_template or is_system)."""
    result: dict[ObjectId, dict[str, Any]] = {}
    for role in db.roles.find(
        {"$or": [{"is_template": True}, {"is_system": True}]},
        {"role_name": 1, "display_name": 1, "permissions": 1},
    ):
        if role.get("role_name") in NON_HOTEL_TEMPLATES:
            continue
        result[role["_id"]] = role
    return result


def _actor_is_assigned_to_role(
    db,
    actor_user_id: ObjectId | None,
    prop_id: int,
    role_id: ObjectId,
) -> bool:
    """True when the actor is the user assigned to ``role_id`` in ``prop_id``.

    The anti self-lockout rule: whoever calls these endpoints is by definition
    an admin of the hotel (``require_prop_permission``) — if their assignment
    points at the role being edited, editing it could strip their own admin
    capability (or worse, they could rename themselves into confusion).
    """
    if not actor_user_id:
        return False
    return bool(
        db.role_assignments.find_one(
            {"user_id": actor_user_id, "prop_id": prop_id, "role_id": role_id},
            {"_id": 1},
        )
    )


def _admin_count(
    db,
    prop_id: int,
    *,
    exclude_user_id: ObjectId | None = None,
    exclude_role_id: ObjectId | None = None,
) -> int:
    """Count distinct active hotel admins (assignment → active role granting manage)."""
    match: dict[str, Any] = {"prop_id": prop_id}
    if exclude_user_id is not None:
        match["user_id"] = {"$ne": exclude_user_id}
    if exclude_role_id is not None:
        match["role_id"] = {"$ne": exclude_role_id}
    pipeline = [
        {"$match": match},
        {"$lookup": {
            "from": "hotel_roles",
            "localField": "role_id",
            "foreignField": "_id",
            "as": "role",
        }},
        {"$unwind": "$role"},
        {"$match": {"role.is_active": True, "role.permissions": HOTEL_MANAGE_ROLES}},
        {"$group": {"_id": "$user_id"}},
        {"$count": "n"},
    ]
    result = list(db.role_assignments.aggregate(pipeline))
    return result[0]["n"] if result else 0


def _assignment_role_grants_manage(db, assignment: dict[str, Any]) -> bool:
    role = db.hotel_roles.find_one(
        {"_id": assignment.get("role_id"), "is_active": True},
        {"permissions": 1},
    )
    return bool(role and HOTEL_MANAGE_ROLES in role.get("permissions", []))


# ── hotel_roles ──


def list_hotel_roles(db, prop_id: int) -> dict[str, Any]:
    roles = list(
        db.hotel_roles.find({"prop_id": prop_id}).sort("name", 1)
    )
    templates = _template_lookup(db)

    # assignment count per role (single query)
    counts: dict[ObjectId, int] = {}
    if roles:
        role_ids = [r["_id"] for r in roles]
        for doc in db.role_assignments.aggregate([
            {"$match": {"role_id": {"$in": role_ids}}},
            {"$group": {"_id": "$role_id", "n": {"$sum": 1}}},
        ]):
            counts[doc["_id"]] = doc["n"]

    items: list[dict[str, Any]] = []
    for role in roles:
        template = templates.get(role.get("based_on_role_id"))
        items.append({
            **role,
            "based_on": (template or {}).get("role_name", ""),
            "assignment_count": counts.get(role["_id"], 0),
        })

    return {
        "items": items,
        "templates": [
            {
                "_id": t["_id"],
                "role_name": t.get("role_name", ""),
                "display_name": t.get("display_name") or t.get("role_name", ""),
                "permissions": t.get("permissions", []),
            }
            for t in templates.values()
        ],
        "permission_codes": sorted(_available_codes(db)),
    }


def create_hotel_role(
    db,
    prop_id: int,
    *,
    name: str,
    display_name: str,
    permissions: list[str],
    based_on_role_id: str | None,
    created_by: str,
) -> dict[str, Any]:
    clean_name = (name or "").strip()
    if not clean_name:
        raise ValueError("El nombre del rol es requerido.")

    template: dict[str, Any] | None = None
    if based_on_role_id:
        try:
            template = db.roles.find_one({"_id": ObjectId(based_on_role_id)})
        except (InvalidId, TypeError):
            template = None
        if not template:
            raise ValueError("La plantilla indicada no existe.")
        # Regla 2: solo roles de plantilla clonables, y nunca los de solo-sistema.
        # El listado ya los oculta; esto cierra la API por si llegan por otro medio.
        if template.get("role_name") in NON_HOTEL_TEMPLATES:
            raise ValueError(SYSTEM_TEMPLATE_MSG)
        if not (template.get("is_template") or template.get("is_system")):
            raise ValueError("La plantilla indicada no es clonable.")

    # Permisos finales: los pedidos; si vienen vacíos y hay plantilla, heredar.
    final_codes = list(permissions or [])
    if not final_codes and template:
        final_codes = list(template.get("permissions", []))
    validated = _validate_permissions(db, final_codes)

    now = _now()
    doc: dict[str, Any] = {
        "prop_id": prop_id,
        "name": clean_name,
        "display_name": (display_name or "").strip() or clean_name,
        "permissions": validated,
        "based_on_role_id": template["_id"] if template else None,
        "is_active": True,
        "is_system": False,
        "created_by": created_by,
        "created_at": now,
        "updated_at": now,
    }
    try:
        db.hotel_roles.insert_one(doc)
    except DuplicateKeyError:
        raise ConflictError(f"Ya existe un rol «{clean_name}» en este hotel.")

    _audit_role(
        db,
        prop_id=prop_id,
        role_id=doc["_id"],
        action="create",
        changed_by=created_by,
        summary=f"Rol «{clean_name}» creado con {len(validated)} permisos.",
        diff={"permissions": {"old": [], "new": validated}},
    )

    return {**doc, "based_on": (template or {}).get("role_name", ""), "assignment_count": 0}


def get_hotel_role(db, prop_id: int, role_id: str) -> dict[str, Any] | None:
    try:
        oid = ObjectId(role_id)
    except (InvalidId, TypeError):
        return None
    return db.hotel_roles.find_one({"_id": oid, "prop_id": prop_id})


def update_hotel_role(
    db,
    prop_id: int,
    role_id: str,
    *,
    display_name: str | None,
    permissions: list[str] | None,
    is_active: bool | None,
    actor_user_id: ObjectId | None = None,
    actor_is_super_admin: bool = False,
    changed_by: str = "system",
) -> dict[str, Any]:
    role = get_hotel_role(db, prop_id, role_id)
    if role is None:
        raise KeyError("role_not_found")
    if role.get("is_system"):
        raise PermissionError("Este rol está protegido y no puede editarse.")
    _ensure_actor_ctx(actor_user_id, actor_is_super_admin)

    # Primero valida el payload (400 si hay permisos desconocidos) para no
    # enmascarar errores de validación detrás del 409 de self-lockout.
    set_fields: dict[str, Any] = {}
    if display_name is not None:
        set_fields["display_name"] = (display_name or "").strip() or role.get("name", "")
    if permissions is not None:
        set_fields["permissions"] = _validate_permissions(db, permissions)
    if is_active is not None:
        set_fields["is_active"] = bool(is_active)

    # Regla 1: el admin no puede editar el rol que tiene asignado (anti self-lockout).
    if not actor_is_super_admin and _actor_is_assigned_to_role(
        db, actor_user_id, prop_id, role["_id"]
    ):
        raise PermissionError(SELF_ROLE_MSG)

    # Anti-lockout: el cambio no puede dejar el hotel sin admin activo.
    old_grants_manage = HOTEL_MANAGE_ROLES in role.get("permissions", [])
    new_grants_manage = old_grants_manage
    if "permissions" in set_fields:
        new_grants_manage = HOTEL_MANAGE_ROLES in set_fields["permissions"]
    if "is_active" in set_fields:
        new_grants_manage = new_grants_manage and set_fields["is_active"]

    if (
        old_grants_manage
        and not new_grants_manage
        and _admin_count(db, prop_id, exclude_role_id=role["_id"]) == 0
    ):
        raise PermissionError(
            "No puedes dejar el hotel sin un rol de administración activo."
        )

    if not set_fields:
        return {**role, "based_on": "", "assignment_count": 0}

    # Diff de auditoría: solo los campos que realmente cambiaron.
    audit_diff: dict[str, Any] = {}
    if "permissions" in set_fields:
        audit_diff["permissions"] = {
            "old": list(role.get("permissions", [])),
            "new": list(set_fields["permissions"]),
        }
    if "display_name" in set_fields and set_fields["display_name"] != role.get("display_name"):
        audit_diff["display_name"] = {
            "old": role.get("display_name", ""),
            "new": set_fields["display_name"],
        }
    if "is_active" in set_fields and set_fields["is_active"] != role.get("is_active"):
        audit_diff["is_active"] = {
            "old": bool(role.get("is_active")),
            "new": bool(set_fields["is_active"]),
        }

    set_fields["updated_at"] = _now()
    db.hotel_roles.update_one({"_id": role["_id"]}, {"$set": set_fields})

    _audit_role(
        db,
        prop_id=prop_id,
        role_id=role["_id"],
        action="update",
        changed_by=changed_by,
        summary=(
            f"Rol «{set_fields.get('display_name') or role.get('name', '')}» "
            f"actualizado ({', '.join(audit_diff.keys()) or 'sin cambios visibles'})."
        ),
        diff=audit_diff or None,
    )

    # Bandeja de notificaciones: cuando los PERMISOS cambian de verdad, avisar
    # a cada miembro asignado al rol ("Tus permisos en {hotel} cambiaron —
    # revisa el historial"). Best-effort: un fallo no revierte la mutación.
    # Comparación por SET: los códigos son únicos y el orden no importa — un
    # PUT que reenvía el mismo set reordenado (rol legacy con array sin
    # normalizar) no debe disparar una notificación fantasma.
    # Decisión: desactivar el rol (is_active=False) NO notifica — pierde el
    # alcance de permisos, pero el request de producto pidió solo cambios de
    # permisos; queda documentado para revisitar.
    permissions_changed = (
        "permissions" in audit_diff
        and set(audit_diff["permissions"]["old"]) != set(audit_diff["permissions"]["new"])
    )
    if permissions_changed:
        notify_role_permissions_changed(
            db,
            prop_id=prop_id,
            role_id=role["_id"],
            role_name=set_fields.get("display_name") or role.get("name", ""),
        )

    updated = db.hotel_roles.find_one({"_id": role["_id"]})
    assignment_count = db.role_assignments.count_documents({"role_id": role["_id"]})
    templates = _template_lookup(db)
    template = templates.get(updated.get("based_on_role_id"))
    return {
        **updated,
        "based_on": (template or {}).get("role_name", ""),
        "assignment_count": assignment_count,
    }


def delete_hotel_role(
    db,
    prop_id: int,
    role_id: str,
    *,
    actor_user_id: ObjectId | None = None,
    actor_is_super_admin: bool = False,
    changed_by: str = "system",
) -> None:
    role = get_hotel_role(db, prop_id, role_id)
    if role is None:
        raise KeyError("role_not_found")
    if role.get("is_system"):
        raise PermissionError("Este rol está protegido y no puede eliminarse.")
    _ensure_actor_ctx(actor_user_id, actor_is_super_admin)
    # Regla 1: el admin no puede eliminar el rol que tiene asignado.
    if not actor_is_super_admin and _actor_is_assigned_to_role(
        db, actor_user_id, prop_id, role["_id"]
    ):
        raise PermissionError(SELF_ROLE_MSG)
    if db.role_assignments.count_documents({"role_id": role["_id"]}) > 0:
        raise PermissionError(
            "No puedes eliminar un rol que tiene personal asignado. "
            "Primero desasigna al personal."
        )
    db.hotel_roles.delete_one({"_id": role["_id"]})

    _audit_role(
        db,
        prop_id=prop_id,
        role_id=role["_id"],
        action="delete",
        changed_by=changed_by,
        summary=f"Rol «{role.get('name', '')}» eliminado.",
        diff={"permissions": {"old": list(role.get("permissions", [])), "new": []}},
    )


# ── Auditoría por rol ──


def get_role_audit(db, prop_id: int, role_id: str) -> dict[str, Any]:
    """Resumen del rol (creador, fechas, plantilla base) + historial de cambios.

    El historial se lee de ``audit_log`` (entity_type="hotel_role") en orden
    cronológico. Roles creados antes del audit trail devuelven ``entries=[]``
    pero conservan los metadatos del documento (``created_by``/fechas).

    Nota: las entradas ``delete`` quedan en ``audit_log`` pero no son visibles
    por este endpoint (el rol ya no existe → 404); se consultan vía el módulo
    de auditoría general.
    """
    role = get_hotel_role(db, prop_id, role_id)
    if role is None:
        raise KeyError("role_not_found")

    templates = _template_lookup(db)
    template = templates.get(role.get("based_on_role_id"))
    entries = list(
        db.audit_log.find(
            {"entity_type": "hotel_role", "entity_id": str(role["_id"])},
            {"_id": 0, "timestamp": 1, "action": 1, "changed_by": 1, "summary": 1, "diff": 1},
        ).sort("timestamp", 1)
    )

    return {
        "_id": role["_id"],
        "name": role.get("name", ""),
        "display_name": role.get("display_name", ""),
        "based_on": (template or {}).get("role_name", ""),
        "created_by": role.get("created_by", ""),
        "created_at": role.get("created_at"),
        "updated_at": role.get("updated_at"),
        "permission_count": len(role.get("permissions", [])),
        "entries": entries,
    }


# ── role_assignments ──


def list_hotel_assignments(db, prop_id: int) -> dict[str, Any]:
    assignments = list(
        db.role_assignments.find({"prop_id": prop_id}).sort("assigned_at", 1)
    )
    assigned_user_ids = [a["user_id"] for a in assignments]

    users_by_id: dict[ObjectId, dict[str, Any]] = {}
    roles_by_id: dict[ObjectId, dict[str, Any]] = {}
    if assigned_user_ids:
        for u in db.users.find(
            {"_id": {"$in": assigned_user_ids}},
            {"username": 1, "display_name": 1, "is_active": 1},
        ):
            users_by_id[u["_id"]] = u
    role_ids = {a.get("role_id") for a in assignments if a.get("role_id")}
    if role_ids:
        for r in db.hotel_roles.find(
            {"_id": {"$in": list(role_ids)}},
            {"name": 1, "display_name": 1},
        ):
            roles_by_id[r["_id"]] = r

    assigned: list[dict[str, Any]] = []
    for a in assignments:
        user = users_by_id.get(a["user_id"], {})
        role = roles_by_id.get(a.get("role_id"), {})
        assigned.append({
            **a,
            "username": user.get("username", ""),
            "display_name": user.get("display_name", ""),
            "role_name": role.get("name", ""),
            "role_display_name": role.get("display_name", ""),
        })

    # Personal del hotel sin asignación todavía.
    staff = list(
        db.users.find(
            {"assigned_hotels": prop_id, "is_active": True},
            {"username": 1, "display_name": 1},
        ).sort("username", 1)
    )
    unassigned = [
        {**u, "user_id": u["_id"]}
        for u in staff
        if u["_id"] not in set(assigned_user_ids)
    ]

    return {"assigned": assigned, "unassigned_staff": unassigned}


def assign_user_to_role(
    db,
    prop_id: int,
    *,
    user_id: str,
    role_id: str,
    assigned_by: str,
    actor_user_id: ObjectId | None = None,
    actor_is_super_admin: bool = False,
) -> dict[str, Any]:
    try:
        uid = ObjectId(user_id)
    except (InvalidId, TypeError):
        raise ValueError("ID de usuario inválido.")
    _ensure_actor_ctx(actor_user_id, actor_is_super_admin)

    # Regla 1: auto-asignarse está prohibido (siempre vía otro admin o super_admin).
    # Se chequea ANTES del duplicado para no quedar enmascarado por
    # "el usuario ya tiene un rol asignado" (el admin siempre tiene asignación).
    if not actor_is_super_admin and uid == actor_user_id:
        raise PermissionError(SELF_ASSIGN_MSG)

    user = db.users.find_one({"_id": uid, "is_active": True})
    if not user:
        raise ValueError("El usuario no existe o está inactivo.")
    # Pertenencia ESTRICTA al hotel. user_can_access_hotel ya es deny-by-
    # default con assigned_hotels vacío, pero aquí el chequeo es sobre el
    # usuario OBJETIVO (no el actor): para recibir un rol, el usuario debe
    # estar explícitamente asignado a este hotel — no basta con el alcance
    # del actor ni con un assigned_prop_id huérfano (onboarding legacy).
    assigned = user.get("assigned_hotels") or []
    if prop_id not in [int(p) for p in assigned]:
        raise ValueError("El usuario no está asignado a este hotel.")

    role = get_hotel_role(db, prop_id, role_id)
    if role is None or not role.get("is_active", True):
        raise ValueError("El rol indicado no existe o está inactivo en este hotel.")

    if db.role_assignments.find_one({"user_id": uid, "prop_id": prop_id}):
        raise ConflictError("El usuario ya tiene un rol asignado en este hotel.")

    now = _now()
    doc: dict[str, Any] = {
        "user_id": uid,
        "prop_id": prop_id,
        "role_id": role["_id"],
        "assigned_by": assigned_by,
        "assigned_at": now,
    }
    try:
        db.role_assignments.insert_one(doc)
    except DuplicateKeyError:
        raise ConflictError("El usuario ya tiene un rol asignado en este hotel.")

    return {
        **doc,
        "username": user.get("username", ""),
        "display_name": user.get("display_name", ""),
        "role_name": role.get("name", ""),
        "role_display_name": role.get("display_name", ""),
    }


def get_assignment(db, prop_id: int, assignment_id: str) -> dict[str, Any] | None:
    try:
        oid = ObjectId(assignment_id)
    except (InvalidId, TypeError):
        return None
    return db.role_assignments.find_one({"_id": oid, "prop_id": prop_id})


def update_assignment_role(
    db,
    prop_id: int,
    assignment_id: str,
    *,
    role_id: str,
    actor_user_id: ObjectId | None = None,
    actor_is_super_admin: bool = False,
) -> dict[str, Any]:
    assignment = get_assignment(db, prop_id, assignment_id)
    if assignment is None:
        raise KeyError("assignment_not_found")
    _ensure_actor_ctx(actor_user_id, actor_is_super_admin)

    role = get_hotel_role(db, prop_id, role_id)
    if role is None or not role.get("is_active", True):
        raise ValueError("El rol indicado no existe o está inactivo en este hotel.")

    # Regla 1: no se puede modificar la propia asignación. Va DESPUÉS de validar
    # el rol destino para no enmascarar errores de validación (400) con el 409.
    if not actor_is_super_admin and assignment["user_id"] == actor_user_id:
        raise PermissionError(OWN_ASSIGNMENT_UPDATE_MSG)

    # Anti-lockout: reasignar al único admin a un rol sin manage → 409.
    old_grants = _assignment_role_grants_manage(db, assignment)
    new_grants = HOTEL_MANAGE_ROLES in role.get("permissions", [])
    if (
        old_grants
        and not new_grants
        and _admin_count(db, prop_id, exclude_user_id=assignment["user_id"]) == 0
    ):
        raise PermissionError(
            "No puedes quitar la administración al último admin del hotel."
        )

    db.role_assignments.update_one(
        {"_id": assignment["_id"]},
        {"$set": {"role_id": role["_id"]}},
    )
    user = db.users.find_one(
        {"_id": assignment["user_id"]},
        {"username": 1, "display_name": 1},
    )
    updated = db.role_assignments.find_one({"_id": assignment["_id"]})
    return {
        **updated,
        "username": (user or {}).get("username", ""),
        "display_name": (user or {}).get("display_name", ""),
        "role_name": role.get("name", ""),
        "role_display_name": role.get("display_name", ""),
    }


def delete_assignment(
    db,
    prop_id: int,
    assignment_id: str,
    *,
    actor_user_id: ObjectId | None = None,
    actor_is_super_admin: bool = False,
) -> None:
    assignment = get_assignment(db, prop_id, assignment_id)
    if assignment is None:
        raise KeyError("assignment_not_found")
    _ensure_actor_ctx(actor_user_id, actor_is_super_admin)

    # Regla 1: no se puede desasignar a uno mismo.
    if not actor_is_super_admin and assignment["user_id"] == actor_user_id:
        raise PermissionError(OWN_ASSIGNMENT_DELETE_MSG)

    # Anti-lockout: no se puede desasignar al último admin del hotel.
    if (
        _assignment_role_grants_manage(db, assignment)
        and _admin_count(db, prop_id, exclude_user_id=assignment["user_id"]) == 0
    ):
        raise PermissionError(
            "No puedes quitar la administración al último admin del hotel. "
            "Designa otro admin antes."
        )

    db.role_assignments.delete_one({"_id": assignment["_id"]})
