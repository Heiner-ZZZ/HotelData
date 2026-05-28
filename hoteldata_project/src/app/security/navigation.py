from __future__ import annotations

from typing import Any


ROLE_DEFAULT_REDIRECTS = {
    "super_admin": "/admin/security",
    "admin_sistema": "/admin/security",
    "operador_datos": "/etl-status",
    "auditor_datos": "/analytics/reservations",
    "hotel_partner": "/partner/hotels",
    "gerente_hotel": "/partner/hotels",
    "revenue_manager": "/analytics/reservations",
    "marketing_hotelero": "/partner/hotels",
    "cliente": "/hotels/search",
}


NAVIGATION_BY_ROLE = {
    "super_admin": [
        {"label": "Seguridad", "href": "/admin/security", "icon": "icon-admin", "permission": "users.manage"},
        {"label": "Usuarios", "href": "/admin/users", "icon": "icon-auth", "permission": "users.manage"},
        {"label": "Dashboard", "href": "/dashboard", "icon": "icon-dashboard", "permission": "dashboard.read"},
        {"label": "CRUD", "href": "/ta02/crud", "icon": "icon-collections", "permission": "crud.read"},
        {"label": "ETL", "href": "/etl-status", "icon": "icon-etl", "permission": "etl.read"},
        {"label": "Cliente", "href": "/hotels/search", "icon": "icon-hotels"},
        {"label": "Reservas", "href": "/reservations", "icon": "icon-booking", "permission": "reservations.manage"},
        {"label": "Partner", "href": "/partner/hotels", "icon": "icon-partner", "permission": "hotels.manage"},
        {"label": "Analytics", "href": "/analytics/reservations", "icon": "icon-analytics", "permission": "dashboard.read"},
        {"label": "Revenue", "href": "/revenue/rate-plans", "icon": "icon-revenue", "permission": "revenue.read"},
        {"label": "Redis", "href": "/system/redis-status", "icon": "icon-records", "permission": "etl.read"},
    ],
    "admin_sistema": [
        {"label": "Seguridad", "href": "/admin/security", "icon": "icon-admin", "permission": "users.manage"},
        {"label": "Usuarios", "href": "/admin/users", "icon": "icon-auth", "permission": "users.manage"},
        {"label": "Dashboard", "href": "/dashboard", "icon": "icon-dashboard", "permission": "dashboard.read"},
        {"label": "CRUD", "href": "/ta02/crud", "icon": "icon-collections", "permission": "crud.read"},
        {"label": "ETL", "href": "/etl-status", "icon": "icon-etl", "permission": "etl.read"},
        {"label": "Redis", "href": "/system/redis-status", "icon": "icon-records", "permission": "etl.read"},
    ],
    "operador_datos": [
        {"label": "ETL", "href": "/etl-status", "icon": "icon-etl", "permission": "etl.read"},
        {"label": "Dashboard", "href": "/dashboard", "icon": "icon-dashboard", "permission": "dashboard.read"},
        {"label": "Auditoría", "href": "/analytics/reservations", "icon": "icon-analytics", "permission": "audit.read"},
        {"label": "Redis", "href": "/system/redis-status", "icon": "icon-records", "permission": "etl.read"},
    ],
    "auditor_datos": [
        {"label": "Reservas", "href": "/analytics/reservations", "icon": "icon-analytics", "permission": "audit.read"},
        {"label": "Conversión", "href": "/analytics/conversion", "icon": "icon-analytics", "permission": "audit.read"},
        {"label": "Revenue", "href": "/analytics/revenue", "icon": "icon-revenue", "permission": "audit.read"},
        {"label": "ETL lectura", "href": "/etl-status", "icon": "icon-etl", "permission": "etl.read"},
    ],
    "hotel_partner": [
        {"label": "Partner", "href": "/partner/hotels", "icon": "icon-partner", "permission": "hotels.manage"},
        {"label": "Reserva manual", "href": "/partner/manual-reservations/new", "icon": "icon-booking", "permission": "reservations.manage"},
        {"label": "Mi sesión", "href": "/auth/me", "icon": "icon-auth"},
    ],
    "gerente_hotel": [
        {"label": "Partner", "href": "/partner/hotels", "icon": "icon-partner", "permission": "hotels.manage"},
        {"label": "Solicitudes", "href": "/reservations", "icon": "icon-booking", "permission": "reservations.manage"},
        {"label": "Reserva manual", "href": "/partner/manual-reservations/new", "icon": "icon-booking", "permission": "reservations.manage"},
        {"label": "Analytics", "href": "/analytics/revenue", "icon": "icon-analytics", "permission": "revenue.read"},
        {"label": "Mi sesión", "href": "/auth/me", "icon": "icon-auth"},
    ],
    "revenue_manager": [
        {"label": "Revenue", "href": "/revenue/rate-plans", "icon": "icon-revenue", "permission": "revenue.read"},
        {"label": "Promociones", "href": "/revenue/promotions", "icon": "icon-revenue", "permission": "revenue.read"},
        {"label": "Analytics", "href": "/analytics/reservations", "icon": "icon-analytics", "permission": "revenue.read"},
        {"label": "Conversión", "href": "/analytics/conversion", "icon": "icon-analytics", "permission": "revenue.read"},
        {"label": "Mercados", "href": "/analytics/visitor-markets", "icon": "icon-analytics", "permission": "revenue.read"},
    ],
    "marketing_hotelero": [
        {"label": "Partner contenido", "href": "/partner/hotels", "icon": "icon-partner", "roles": ("marketing_hotelero",)},
        {"label": "Promociones", "href": "/revenue/promotions", "icon": "icon-revenue", "permission": "revenue.read"},
        {"label": "Analytics promo", "href": "/analytics/promotions", "icon": "icon-analytics", "permission": "revenue.read"},
    ],
    "cliente": [
        {"label": "Hoteles", "href": "/hotels/search", "icon": "icon-hotels"},
        {"label": "Reservas", "href": "/reservations", "icon": "icon-booking", "roles": ("cliente",)},
        {"label": "Mi sesión", "href": "/auth/me", "icon": "icon-auth"},
    ],
}


def get_default_redirect_for_role(role_name: str | None) -> str:
    return ROLE_DEFAULT_REDIRECTS.get(role_name or "", "/hotels/search")


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
