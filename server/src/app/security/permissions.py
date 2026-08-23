"""Permission resolution with wildcard expansion.

Permission codes follow the format ``{resource}.{action}`` where:
- ``action`` is one of: create, read, update, delete, execute, manage
- ``manage`` is a wildcard that expands to all CRUD actions for that resource
- ``execute`` is for ETL/data-pipeline operations (no CRUD expansion)

Expansion example:
    ``reservations.manage``  →  reservations.create, .read, .update, .delete
    ``etl.execute``          →  etl.execute  (no expansion)

super_admin always gets a sentinel ``*.*`` that bypasses all checks.
"""

from __future__ import annotations

import logging
from typing import Any

from bson import ObjectId
from pymongo.database import Database

from src.app.security.role_helpers import get_role_name, is_super_admin, is_unfiltered_role

logger = logging.getLogger(__name__)

# Actions that ``.manage`` expands into
_MANAGE_CRUD_ACTIONS = ("create", "read", "update", "delete")

# Actions whose grant implies the resource's ``read`` permission. Any other
# action (e.g. the compound ``hotel.manage_roles``, ``properties.approve``,
# ``hr.onboarding.create``) is a standalone code that must pass through
# unchanged — those resources have no ``<resource>.read`` sibling in the
# catalog.
# KEEP IN SYNC: admin/routes.py (_PREVIEW_READ_DEP_ACTIONS) y
# admin/service/role_update.py (missing_read check).
READ_DEP_ACTIONS = frozenset({"create", "update", "delete", "manage", "execute"})

# Sensitive operational capability: a receptionist can complete a normal or
# courtesy check-in, but only a hotel manager (or super_admin bypass) may
# authorize an arrival outside the courtesy window.
EARLY_CHECK_IN_APPROVAL_PERMISSION = "check-ins.early_approve"

# Reabrir una reserva ya marcada como no-show es una autorización gerencial:
# el huésped llegó después de que el no-show fue cerrado (política de llegadas),
# así que la recepción no puede hacerlo por sí sola.
NO_SHOW_REOPEN_PERMISSION = "check-ins.no_show_reopen"

# Autorizar un late check-out fuera de la ventana de cortesía es igual de
# sensible que el early approve: la recepción completa el check-out normal o
# dentro de la cortesía, pero solo el gerente (o super_admin) puede extender
# la salida más allá de la gracia configurada en la política del hotel.
LATE_CHECKOUT_APPROVAL_PERMISSION = "check-ins.late_checkout_approve"

# Role allow-list compartida por las tres autorizaciones gerenciales (early
# approve, no-show reopen, late check-out approve). Defensa en profundidad:
# aunque alguien otorgue el código de permiso a un rol de recepción, el gate
# exige además que el rol primario esté en esta lista.
MANAGER_AUTHORIZATION_ROLES = frozenset({"gerente_hotel", "super_admin"})

# ── Autorizaciones de supervisor (mismo patrón, allow-list distinta) ──
# Cerrar un folio CON SALDO mediante una excepción (write-off, cortesía o
# settlement externo) es un ajuste financiero: la recepción tiene
# ``billing.manage`` pero NO puede condonar saldos sin aprobación. El gate
# reutiliza ``require_manager_authorization`` con esta allow-list (agrega
# ``admin_sistema`` como supervisor de nivel sistema).
FOLIO_ADJUST_APPROVAL_PERMISSION = "billing.write_off.approve"
SUPERVISOR_AUTHORIZATION_ROLES = frozenset({"gerente_hotel", "admin_sistema", "super_admin"})

# Guest-facing codes (auto-servicio del huésped — sección "Cliente" del editor
# de roles). super_admin conserva el bypass ``*.*`` para AUTH (``user_has_permission``
# sigue devolviendo True), pero estos códigos NO se le otorgan en el editor ni se
# le muestran los ítems de navegación que los exigen (Buscar Hoteles / Mis Reservas
# / Mi Perfil): el menú HUÉSPED es auto-servicio del cliente, no del administrador
# del sistema. Decisión 2026-08.
# KEEP IN SYNC: scripts/init_security_model_ga03.py (GUEST_PERMISSION_CODES).
GUEST_PERMISSION_CODES = frozenset({
    "account.manage",
    "account.read",
    "account.update",
    "account.bookings.read",
    "search.manage",
    "search.read",
})

# ── Platform-scoped codes (solo super admin / plataforma) ─────────────────
# Permisos que NO son operativos del hotel: gestión de usuarios/roles,
# ETL, auditoría, monitoreo, settings globales, cola de aprobación de
# hoteles y la cartera estratégica (Vista B). Un gerente creando un rol de
# empleado NO debe verlos ni poder otorgarlos — el editor del hotel
# (``list_hotel_roles``) los filtra y la API los rechaza (400).
# KEEP IN SYNC: scripts/init_security_model_ga03.py (SYSTEM_SCOPE_CODES).
SYSTEM_SCOPE_CODES = frozenset({
    # Usuarios y roles (plataforma)
    "users.manage", "users.create", "users.read", "users.update", "users.delete",
    "roles.manage", "roles.create", "roles.read", "roles.update", "roles.delete",
    # Aprobación de nuevos hoteles (cola del admin)
    "properties.approve",
    # Configuración / auditoría / monitoreo / ETL (plataforma)
    "settings.manage", "settings.read",
    "audit.manage", "audit.read",
    "monitoring.manage", "monitoring.read",
    "etl.manage", "etl.read", "etl.execute",
    # Cartera estratégica del sistema (Vista B) — solo dirección
    "reports.strategic.portfolio.read",
})


def permission_scope(code: str) -> str:
    """Categoría de visibilidad de un código de permiso (C 2026-08).

    - ``system`` → plataforma / super admin (usuarios, roles, ETL, auditoría,
      settings, properties.approve, cartera estratégica). NO se exponen en el
      editor de roles del hotel ni se otorgan a roles de hotel.
    - ``guest`` → auto-servicio del huésped (``GUEST_PERMISSION_CODES``).
      Tampoco son códigos operativos del hotel.
    - ``hotel`` → por defecto: operación del hotel (reservas, billing,
      housekeeping, RRHH, check-ins…). Únicos códigos que el gerente puede
      otorgar a sus roles de equipo.
    """
    if code in SYSTEM_SCOPE_CODES:
        return "system"
    if code in GUEST_PERMISSION_CODES:
        return "guest"
    return "hotel"

# ── Allow-lists de quién puede portar códigos system/guest (C 2026-08) ──
# Lógica dura: los roles operativos de hotel (recepcionista, gerente_hotel,
# housekeeping…) NO portan códigos de plataforma (system) ni de auto-servicio
# del huésped (guest). Estas allow-lists son las únicas excepciones:
#   - PLATFORM_ROLES: roles de plataforma que pueden portar system codes
#     (admin_sistema opera la plataforma; operador_datos/auditor_datos son
#     roles de datos/ETL). super_admin es la excepción implícita (bypass *.*).
#   - GUEST_ROLES: el huésped puede portar guest codes.
# El seed canónico las duplica (KEEP IN SYNC) y el editor global de roles
# (update_role_definition) las aplica en runtime.
# KEEP IN SYNC: scripts/init_security_model_ga03.py (PLATFORM_ROLES/GUEST_ROLES).
PLATFORM_ROLES = frozenset({"admin_sistema", "operador_datos", "auditor_datos"})
GUEST_ROLES = frozenset({"cliente"})


def ensure_read_dependencies(
    explicit_codes: set[str],
    available_codes: set[str] | None = None,
) -> set[str]:
    """Ensure every non-read action has its resource's ``read`` permission.

    The editor and API both use this invariant: an actor cannot be granted
    create/update/delete/manage/execute access to a resource without being
    able to read that resource's UI/data. When a catalog is supplied, only
    existing permission codes are added.
    """
    normalized = set(explicit_codes)
    for code in tuple(explicit_codes):
        if "." not in code:
            continue
        resource, action = code.split(".", 1)
        if action == "read":
            continue
        read_code = f"{resource}.read"
        if available_codes is None or read_code in available_codes:
            normalized.add(read_code)
    return normalized


def expand_permissions(explicit_codes: set[str]) -> set[str]:
    """Expand wildcard ``resource.manage`` into individual CRUD permissions.

    - ``*.*`` (super_admin sentinel) is returned as-is.
    - ``resource.manage`` expands to resource.create, .read, .update, .delete
    - All other codes pass through unchanged.
    """
    if "*.*" in explicit_codes:
        return {"*.*"}
    expanded = set(explicit_codes)
    for code in explicit_codes:
        if "." not in code:
            continue
        resource, action = code.split(".", 1)
        if action == "manage":
            expanded.update({f"{resource}.{a}" for a in _MANAGE_CRUD_ACTIONS})
    return expanded


def _normalize_role_ids(user: dict[str, Any]) -> list[ObjectId]:
    role_ids: list[ObjectId] = []
    for role_id in user.get("role_ids", []) or []:
        if isinstance(role_id, ObjectId):
            role_ids.append(role_id)
        elif isinstance(role_id, str) and ObjectId.is_valid(role_id):
            role_ids.append(ObjectId(role_id))
    return role_ids


def _get_hotel_scoped_codes(
    db: Database,
    user: dict[str, Any],
    prop_id: int,
) -> set[str]:
    """Resolve hotel-scoped permission codes for ``user`` in ``prop_id``.

    Fase 1 RBAC por hotel (``docs/PERMISOS_POR_HOTEL.md``). Deny-by-default:

    1. Look up the user's ``role_assignments`` row for the hotel.
    2. No assignment → empty set (deny). The global role is NEVER used as a
       fallback here — doing so would let a restricted hotel-1 employee gain
       the global role's permissions on hotel-2 routes (cross-hotel escalation).
    3. Assignment found → the ``hotel_roles`` doc is authoritative: an
       inactive or missing hotel role also denies (empty set).
    """
    assignment = db.role_assignments.find_one(
        {"user_id": user["_id"], "prop_id": int(prop_id)}
    )
    if not assignment:
        return set()
    role = db.hotel_roles.find_one(
        {"_id": assignment.get("role_id"), "is_active": True}
    )
    if not role:
        return set()
    return expand_permissions(set(role.get("permissions", [])))


def get_user_permission_codes(
    db: Database,
    user: dict[str, Any],
    prop_id: int | None = None,
) -> set[str]:
    """Return the expanded set of permission codes for a user.

    Reads from the ``roles.permissions`` embedded array (canonical source)
    when no hotel context is given.

    When ``prop_id`` is provided (Fase 1 hotel-scoped RBAC), permissions are
    resolved STRICTLY from ``role_assignments`` → ``hotel_roles`` for that
    hotel: no assignment for the hotel means no permissions (deny-by-default,
    per ``docs/PERMISOS_POR_HOTEL.md``). The global role resolution below is
    only used when no hotel context is given (legacy ``require_permission``
    paths and system roles).
    """
    if not user:
        return set()
    if is_super_admin(user):
        return {"*.*"}

    if prop_id is not None:
        # Unfiltered roles (cliente, admin_sistema) bypass hotel-scoped RBAC.
        # They don't have role_assignments (guests aren't staff; platform roles
        # operate across all hotels) — their permissions resolve globally.
        if is_unfiltered_role(user):
            prop_id = None  # fall through to global resolution
        else:
            return _get_hotel_scoped_codes(db, user, prop_id)

    role_ids = _normalize_role_ids(user)
    primary_role = get_role_name(user)
    if primary_role:
        role = db.roles.find_one({"role_name": primary_role})
        if role and role["_id"] not in role_ids:
            role_ids.append(role["_id"])
        elif not role:
            logger.debug(
                "permissions.primary_role_unresolved user=%s primary_role=%s",
                user.get("username"),
                primary_role,
            )
    if not role_ids:
        return set()

    # ── Read from roles.permissions embedded array (canonical source) ──
    explicit: set[str] = set()
    for r in db.roles.find({"_id": {"$in": role_ids}}, {"permissions": 1}):
        explicit.update(r.get("permissions", []))

    return expand_permissions(explicit)


def user_has_permission(
    db: Database,
    user: dict[str, Any] | None,
    permission_code: str,
    prop_id: int | None = None,
) -> bool:
    """Check whether a user has a specific permission.

    ``super_admin`` always returns ``True``.
    Inactive users always return ``False``.

    When ``prop_id`` is provided (Fase 1 hotel-scoped RBAC), permissions are
    resolved strictly from the user's ``role_assignments`` → ``hotel_roles``
    for that hotel — no assignment means deny (no global fallback).
    """
    if not user or not user.get("is_active", True):
        return False
    if is_super_admin(user):
        return True
    codes = get_user_permission_codes(db, user, prop_id=prop_id)
    if "*.*" in codes:
        return True
    return permission_code in codes


def require_supervisor_authorization(
    db: Database,
    user: dict[str, Any] | None,
    *,
    permission_code: str,
    allowed_roles: frozenset[str] | set[str] | None = None,
) -> bool:
    """Supervisor-level authorization — same unified gate, different allow-list.

    Reusa ``require_manager_authorization`` completo (inactivo → False,
    super_admin bypass, role allow-list + permiso embebido) cambiando el
    default de ``allowed_roles`` a ``SUPERVISOR_AUTHORIZATION_ROLES``. Es el
    patrón para áreas donde la aprobación exige un supervisor distinto del
    gerente operativo (ej. ajustes del folio / write-off).
    """
    return require_manager_authorization(
        db,
        user,
        permission_code=permission_code,
        allowed_roles=allowed_roles if allowed_roles is not None else SUPERVISOR_AUTHORIZATION_ROLES,
    )


def require_manager_authorization(
    db: Database,
    user: dict[str, Any] | None,
    *,
    permission_code: str,
    allowed_roles: frozenset[str] | set[str] | None = None,
) -> bool:
    """Return whether ``user`` may perform a sensitive manager-only operation.

    Single gate for the three operational authorizations that share one
    contract (early check-in approval, no-show reopen, late check-out
    approval): the capability is catalogued for the manager role, and the
    role allow-list is intentional defense in depth — it prevents an ad-hoc
    front-desk role grant from silently becoming an approval authority even
    if the permission code were added to a receptionist role.

    - Inactive users always return False.
    - ``super_admin`` always bypasses (sentinel ``*.*`` / primary role).
    - ``allowed_roles`` (default ``MANAGER_AUTHORIZATION_ROLES``) narrows the
      gate to the documented roles; a user whose primary role is not in the
      list is denied regardless of the permission.
    """
    if not user or not user.get("is_active", True):
        return False
    if is_super_admin(user):
        return True
    if allowed_roles is None:
        allowed_roles = MANAGER_AUTHORIZATION_ROLES
    if get_role_name(user) not in allowed_roles:
        return False
    return user_has_permission(db, user, permission_code)
