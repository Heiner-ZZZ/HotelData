from __future__ import annotations

from typing import Any


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
        {"label": "Mi Portal", "href": "/management/hr/my-portal", "icon": "icon-dashboard"},
        {"label": "Housekeeping", "href": "/management/housekeeping", "icon": "icon-cleaning"},
    ],
    "cliente": [
        {"label": "Hoteles", "href": "/search", "icon": "icon-hotels"},
        {"label": "Reservas", "href": "/account/bookings", "icon": "icon-booking", "roles": ("cliente",)},
        {"label": "Perfil", "href": "/account/profile", "icon": "icon-auth"},
    ],
}


def get_default_redirect_for_role(role_name: str | None) -> str:
    return ROLE_DEFAULT_REDIRECTS.get(role_name or "", "/search")


def get_navigation_for_role(role_name: str | None, permission_codes: set[str] | None = None) -> list[dict[str, str]]:
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
    return get_navigation_for_role(user.get("primary_role"), permission_codes)
