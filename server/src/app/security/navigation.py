from __future__ import annotations

from typing import Any

from src.app.security.permissions import GUEST_PERMISSION_CODES
from src.app.security.role_helpers import get_role_name, is_super_admin


ROLE_DEFAULT_REDIRECTS = {
    "super_admin": "/system/users",
    "admin_sistema": "/system/users",
    "operador_datos": "/system/monitoring",
    "auditor_datos": "/system/audit",
    "hotel_partner": "/management",
    "gerente_hotel": "/management",
    "revenue_manager": "/management/rates",
    "marketing_hotelero": "/management/amenities",
    "maintenance": "/management/hr/my-portal",
    "recepcionista": "/management/reservations",
    "housekeeping": "/management/housekeeping",
    "concierge": "/management/reservations",
    "cliente": "/search",
}


NAVIGATION_BY_ROLE: dict[str, list[dict[str, Any]]] = {
    "super_admin": [
        {"label": "Sistema", "href": "/system/users", "icon": "icon-admin", "permission": "users.manage"},
        {"label": "Permisos", "href": "/system/permissions", "icon": "icon-auth", "permission": "users.manage"},
        {"label": "Gestion", "href": "/management", "icon": "icon-dashboard", "permission": "dashboard.read"},
        {"label": "Operaciones", "href": "/management/reservations", "icon": "icon-booking", "permission": "reservations.manage"},
        {"label": "Catalogo", "href": "/management/properties", "icon": "icon-partner", "permission": "hotels.manage"},
        {"label": "Cliente", "href": "/search", "icon": "icon-hotels"},
        {"label": "Monitoreo", "href": "/system/monitoring", "icon": "icon-records", "permission": "etl.read"},
    ],
    "admin_sistema": [
        {"label": "Sistema", "href": "/system/users", "icon": "icon-admin", "permission": "users.manage"},
        {"label": "Permisos", "href": "/system/permissions", "icon": "icon-auth", "permission": "users.manage"},
        {"label": "Auditoria", "href": "/system/audit", "icon": "icon-analytics", "permission": "dashboard.read"},
        {"label": "Monitoreo", "href": "/system/monitoring", "icon": "icon-records", "permission": "etl.read"},
    ],
    "operador_datos": [
        {"label": "Monitoreo", "href": "/system/monitoring", "icon": "icon-records", "permission": "etl.read"},
        {"label": "Gestion", "href": "/management", "icon": "icon-dashboard", "permission": "dashboard.read"},
        {"label": "Reportes", "href": "/management/reports", "icon": "icon-analytics", "permission": "audit.read"},
    ],
    "auditor_datos": [
        {"label": "Auditoria", "href": "/system/audit", "icon": "icon-analytics", "permission": "audit.read"},
        {"label": "Reportes", "href": "/management/reports", "icon": "icon-revenue", "permission": "audit.read"},
        {"label": "Monitoreo", "href": "/system/monitoring", "icon": "icon-records", "permission": "etl.read"},
    ],
    "hotel_partner": [
        {"label": "Panel", "href": "/management", "icon": "icon-dashboard", "permission": "hotels.manage"},
        {"label": "Propiedades", "href": "/management/properties", "icon": "icon-partner", "permission": "hotels.manage"},
        {"label": "Reservas", "href": "/management/reservations", "icon": "icon-booking", "permission": "reservations.manage"},
    ],
    "gerente_hotel": [
        {"label": "Panel", "href": "/management", "icon": "icon-dashboard", "permission": "hotels.manage"},
        {"label": "Reservas", "href": "/management/reservations", "icon": "icon-booking", "permission": "reservations.manage"},
        {"label": "Disponibilidad", "href": "/management/availability", "icon": "icon-partner", "permission": "hotels.manage"},
        {"label": "Tarifas", "href": "/management/rates", "icon": "icon-analytics", "permission": "revenue.read"},
    ],
    "revenue_manager": [
        {"label": "Tarifas", "href": "/management/rates", "icon": "icon-revenue", "permission": "revenue.read"},
        {"label": "Inventario", "href": "/management/availability", "icon": "icon-partner", "permission": "revenue.read"},
        {"label": "Reservas", "href": "/management/reservations", "icon": "icon-booking", "permission": "revenue.read"},
        {"label": "Reportes", "href": "/management/reports", "icon": "icon-analytics", "permission": "revenue.read"},
    ],
    "marketing_hotelero": [
        {"label": "Contenido", "href": "/management/properties", "icon": "icon-partner", "roles": ("marketing_hotelero",)},
        {"label": "Amenities", "href": "/management/amenities", "icon": "icon-revenue", "permission": "revenue.read"},
        {"label": "Reportes", "href": "/management/reports", "icon": "icon-analytics", "permission": "revenue.read"},
    ],
    "maintenance": [
        {"label": "Mi Portal", "href": "/management/hr/my-portal", "icon": "icon-dashboard", "permission": "hr.read"},
        {"label": "Housekeeping", "href": "/management/housekeeping", "icon": "icon-cleaning"},
    ],
    "recepcionista": [
        {"label": "Reservas", "href": "/management/reservations", "icon": "icon-booking", "permission": "reservations.manage"},
        {"label": "Check-ins", "href": "/management/check-ins", "icon": "icon-dashboard", "permission": "check-ins.manage"},
        {"label": "Check-outs", "href": "/management/check-outs", "icon": "icon-dashboard", "permission": "check-outs.manage"},
        {"label": "Recepción", "href": "/management/recepcion", "icon": "icon-booking", "permission": "reservations.read"},
        {"label": "Mi Portal", "href": "/management/hr/my-portal", "icon": "icon-dashboard", "permission": "hr.read"},
    ],
    "housekeeping": [
        {"label": "Mi Portal", "href": "/management/hr/my-portal", "icon": "icon-dashboard", "permission": "hr.read"},
        {"label": "Housekeeping", "href": "/management/housekeeping", "icon": "icon-cleaning", "permission": "housekeeping.read"},
        {"label": "Mantenimiento", "href": "/management/housekeeping/maintenance", "icon": "icon-dashboard", "permission": "maintenance.read"},
    ],
    "concierge": [
        {"label": "Reservas", "href": "/management/reservations", "icon": "icon-booking", "permission": "reservations.read"},
        {"label": "Huéspedes", "href": "/management/guests", "icon": "icon-admin", "permission": "reservations.read"},
        {"label": "Amenities", "href": "/management/amenities", "icon": "icon-dashboard", "permission": "amenities.read"},
        {"label": "Mi Portal", "href": "/management/hr/my-portal", "icon": "icon-dashboard", "permission": "hr.read"},
    ],
    "cliente": [
        {"label": "Hoteles", "href": "/search", "icon": "icon-hotels"},
        {"label": "Reservas", "href": "/account/bookings", "icon": "icon-booking", "roles": ("cliente",)},
        {"label": "Perfil", "href": "/account/profile", "icon": "icon-auth"},
    ],
}


def get_default_redirect_for_role(role_name: str | None) -> str:
    return ROLE_DEFAULT_REDIRECTS.get(role_name or "", "/search")


def get_all_navigation_items(permission_codes: set[str] | None = None) -> list[dict[str, Any]]:
    """Read ALL navigation nodes from the ``navigation`` DB collection as a
    flat list with ancestor-aware ``visible`` flags.

    Cada nodo lleva su posición en el árbol (``slug``, ``parent_slug``,
    ``position``, ``node_type``). ``visible`` se computa top-down: un nodo es
    visible solo si su ``permission_code`` está satisfecho Y todos sus
    ancestros son visibles, así un container oculto nunca filtra sus hijos.

    Returns empty list if the collection doesn't exist yet (graceful degradation).
    """
    try:
        from src.database.connection import get_database
        db = get_database()
        docs = list(db.navigation.find({}).sort([("parent_slug", 1), ("position", 1)]))

        by_slug: dict[str, dict[str, Any]] = {}
        for doc in docs:
            slug = doc.get("slug")
            if slug:
                by_slug[slug] = doc

        def _self_visible(required: str | None) -> bool:
            if not required or permission_codes is None:
                return True
            if "*.*" in permission_codes:
                # Bypass de super_admin: ve TODO el menú EXCEPTO el auto-servicio
                # del huésped (account.*/search.*), igual que antes.
                return required not in GUEST_PERMISSION_CODES
            return required in permission_codes

        memo: dict[str, bool] = {}

        def _visible(slug: str | None) -> bool:
            if not slug or slug not in by_slug:
                return True
            if slug in memo:
                return memo[slug]
            memo[slug] = False  # guard contra ciclos mientras se resuelve
            doc = by_slug[slug]
            parent_ok = _visible(doc.get("parent_slug"))
            self_ok = _self_visible(doc.get("permission_code"))
            result = parent_ok and self_ok
            memo[slug] = result
            return result

        # Podar containers sin hojas visibles: una sección vacía (p.ej.
        # "Huésped" para super_admin, cuyos hijos son todos auto-servicio del
        # cliente) no debe aparecer en el sidebar. La visibilidad es top-down
        # (``parent_ok`` corta la cadena), así que un nodo invisible no puede
        # tener descendientes visibles: basta con verificar hojas visibles
        # bajo cada container.
        leaf_memo: dict[str, bool] = {}

        def _has_visible_leaf(slug: str | None) -> bool:
            if not slug or slug not in by_slug:
                return False
            if slug in leaf_memo:
                return leaf_memo[slug]
            leaf_memo[slug] = False  # guard contra ciclos mientras se resuelve
            for child in by_slug.values():
                if child.get("parent_slug") != slug:
                    continue
                child_slug = child.get("slug")
                if not _visible(child_slug):
                    continue
                if child.get("node_type") == "leaf" or _has_visible_leaf(child_slug):
                    leaf_memo[slug] = True
                    break
            return leaf_memo[slug]

        items: list[dict[str, Any]] = []
        for doc in docs:
            slug = doc.get("slug")
            pid = doc.get("permission_id")
            visible = _visible(slug)
            if visible and doc.get("node_type") != "leaf":
                visible = _has_visible_leaf(slug)
            items.append({
                "slug": slug or "",
                "parentSlug": doc.get("parent_slug"),
                "position": doc.get("position", 0),
                "nodeType": doc.get("node_type"),
                "label": doc.get("label", ""),
                "href": doc.get("href", ""),
                "icon": doc.get("icon", ""),
                "visible": visible,
                "permissionId": str(pid) if pid else None,
                "permissionCode": doc.get("permission_code"),
                "horizontalMenu": bool(doc.get("horizontal_menu", False)),
            })
        return items
    except Exception:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("navigation.get_all_navigation_items failed", exc_info=True)
        return []


def get_navigation_for_role(role_name: str | None, permission_codes: set[str] | None = None) -> list[dict[str, str]]:
    # ── Try DB-based navigation first ──
    db_items = get_all_navigation_items(permission_codes)
    if db_items:
        return [
            {"label": item["label"], "href": item["href"], "icon": item["icon"]}
            for item in db_items if item.get("visible") and item.get("href")
        ]

    # ── Fallback to hardcoded NAVIGATION_BY_ROLE ──
    items = NAVIGATION_BY_ROLE.get(role_name or "", NAVIGATION_BY_ROLE["cliente"])
    if not permission_codes or role_name == "super_admin":
        return [{"label": item["label"], "href": item["href"], "icon": item["icon"]} for item in items]

    visible_items: list[dict[str, str]] = []
    for item in items:
        required_permission = item.get("permission")
        allowed_roles = item.get("roles", ())
        if required_permission and required_permission not in permission_codes:
            continue
        if allowed_roles and role_name not in allowed_roles and role_name != "super_admin":
            continue
        visible_items.append({"label": item["label"], "href": item["href"], "icon": item["icon"]})
    return visible_items


def get_navigation_for_user(user: dict[str, Any] | None, permission_codes: set[str] | None = None) -> list[dict[str, str]]:
    if not user:
        return [{"label": "Login", "href": "/auth/login", "icon": "icon-auth"}]
    return get_navigation_for_role(get_role_name(user), permission_codes)
