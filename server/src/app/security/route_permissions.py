from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AccessRule:
    prefix: str
    methods: tuple[str, ...] = ("GET", "POST", "PUT", "PATCH", "DELETE")
    permission: str | None = None
    roles: tuple[str, ...] = ()


PUBLIC_PREFIXES = ("/static", "/api/hotels")
PUBLIC_PATHS = ("/login", "/auth/login", "/api/auth/login", "/api/auth/register", "/api/auth/send-code", "/api/auth/confirm-code", "/api/auth/refresh", "/api/auth/me", "/api/auth/status", "/api/auth/recover", "/api/auth/reset", "/api/auth/recover/reset", "/auth/logout")


ROUTE_RULES = [
    AccessRule("/admin/security", permission="users.manage", roles=("super_admin", "admin_sistema")),
    AccessRule("/admin/users", permission="users.manage", roles=("super_admin", "admin_sistema")),
    AccessRule("/api/admin/security", permission="users.manage", roles=("super_admin", "admin_sistema")),
    AccessRule("/api/admin/users", permission="users.manage", roles=("super_admin", "admin_sistema")),
    AccessRule("/api/admin/permissions", permission="users.manage", roles=("super_admin", "admin_sistema")),
    AccessRule("/api/admin/ownership", permission="users.manage", roles=("super_admin", "admin_sistema")),
    AccessRule("/dashboard", permission="dashboard.read"),
    AccessRule("/api/dashboard", permission="dashboard.read"),
    AccessRule("/api/reviews/guest", roles=("cliente", "super_admin", "admin_sistema", "hotel_partner", "gerente_hotel")),
    AccessRule("/api/reviews/staff", roles=("super_admin", "admin_sistema", "hotel_partner", "gerente_hotel")),
    AccessRule("/api/reviews", roles=("cliente", "super_admin", "admin_sistema", "hotel_partner", "gerente_hotel", "marketing_hotelero")),
    AccessRule("/api/reservations", roles=("cliente", "super_admin", "admin_sistema", "hotel_partner", "gerente_hotel")),
    AccessRule("/api/admin/notifications", permission="users.manage", roles=("super_admin", "admin_sistema")),
    AccessRule("/api/housekeeping",
        roles=("super_admin", "admin_sistema", "hotel_partner", "gerente_hotel", "revenue_manager", "marketing_hotelero", "operador_datos", "auditor_datos"),
    ),
    AccessRule("/api/tracking",
        roles=("super_admin", "admin_sistema", "cliente", "hotel_partner", "gerente_hotel",
               "revenue_manager", "marketing_hotelero", "operador_datos", "auditor_datos"),
    ),
    # Heartbeat — must bypass permission checks so the frontend can keep
    # the inactivity timeout alive even when the user lacks crud.write.
    AccessRule("/api/auth/heartbeat",
        roles=("super_admin", "admin_sistema", "cliente", "hotel_partner", "gerente_hotel",
               "revenue_manager", "marketing_hotelero", "operador_datos", "auditor_datos"),
    ),
    AccessRule("/api/account", roles=("cliente", "super_admin", "admin_sistema")),
    AccessRule("/api/settings",
        roles=("cliente", "super_admin", "admin_sistema", "hotel_partner", "gerente_hotel", "revenue_manager", "marketing_hotelero", "operador_datos", "auditor_datos"),
    ),
    AccessRule("/api/management/products",
        roles=("super_admin", "admin_sistema", "hotel_partner", "gerente_hotel", "revenue_manager", "marketing_hotelero", "operador_datos", "auditor_datos", "cliente"),
    ),
    AccessRule("/api/management",
        roles=("super_admin", "admin_sistema", "hotel_partner", "gerente_hotel", "revenue_manager", "marketing_hotelero", "operador_datos", "auditor_datos"),
    ),
    AccessRule("/ta02/crud", methods=("GET",), permission="crud.read"),
    AccessRule("/ta02/crud", methods=("POST", "PUT", "PATCH", "DELETE"), permission="crud.write"),
    AccessRule("/api", methods=("GET",), permission="crud.read"),
    AccessRule("/api", methods=("POST", "PUT", "PATCH", "DELETE"), permission="crud.write"),
    AccessRule("/etl-status/ga03", methods=("POST",), permission="etl.execute"),
    AccessRule("/etl-status/upload", methods=("POST",), permission="etl.execute"),
    AccessRule("/etl-status/seed", methods=("POST",), permission="etl.execute"),
    AccessRule("/etl-status/run", methods=("POST",), permission="etl.execute"),
    AccessRule("/etl-status", methods=("GET",), permission="etl.read"),
    AccessRule("/system/redis-status", permission="etl.read", roles=("super_admin", "admin_sistema")),
    AccessRule("/partner/manual-reservations", permission="reservations.manage"),
    AccessRule("/partner", permission="hotels.manage", roles=("marketing_hotelero",)),
    AccessRule("/revenue/rate-plans/new", methods=("GET",), permission="revenue.manage"),
    AccessRule("/revenue/promotions/new", methods=("GET",), permission="revenue.manage"),
    AccessRule("/revenue", methods=("GET",), permission="revenue.read"),
    AccessRule("/revenue", methods=("POST", "PUT", "PATCH", "DELETE"), permission="revenue.manage"),
    AccessRule("/analytics", roles=("super_admin", "admin_sistema", "operador_datos", "auditor_datos", "gerente_hotel", "revenue_manager", "marketing_hotelero")),
    AccessRule("/reservations", roles=("cliente", "super_admin", "admin_sistema", "hotel_partner", "gerente_hotel")),
    AccessRule("/hotels", roles=("cliente", "super_admin", "admin_sistema", "operador_datos", "auditor_datos", "hotel_partner", "gerente_hotel", "revenue_manager", "marketing_hotelero")),
    AccessRule("/ta02", roles=("super_admin", "admin_sistema", "operador_datos")),
    AccessRule("/records", roles=("super_admin", "admin_sistema", "operador_datos")),
    AccessRule("/quality", permission="audit.read"),
    AccessRule("/collections", permission="crud.read"),
    AccessRule("/problems", permission="audit.read"),
    AccessRule("/catalogs", permission="crud.read"),
    AccessRule("/api/audit", permission="audit.read", roles=("auditor_datos", "super_admin", "admin_sistema", "operador_datos")),
    AccessRule("/audit", permission="audit.read", roles=("auditor_datos", "super_admin", "admin_sistema", "operador_datos")),
    AccessRule("/company", permission="dashboard.read"),
]


def is_public_path(path: str) -> bool:
    return path in PUBLIC_PATHS or any(path.startswith(prefix) for prefix in PUBLIC_PREFIXES)


def is_safe_internal_next(next_url: str | None) -> bool:
    if not next_url:
        return False
    return next_url.startswith("/") and not next_url.startswith("//") and "://" not in next_url


def get_access_rule(path: str, method: str) -> AccessRule | None:
    matches = [
        rule
        for rule in ROUTE_RULES
        if path.startswith(rule.prefix) and method.upper() in rule.methods
    ]
    if not matches:
        return AccessRule(path, roles=("super_admin", "admin_sistema"))
    return max(matches, key=lambda rule: len(rule.prefix))


def role_allowed(user: dict[str, Any], allowed_roles: tuple[str, ...]) -> bool:
    primary_role = user.get("primary_role")
    return primary_role == "super_admin" or primary_role in allowed_roles
