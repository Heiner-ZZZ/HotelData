from __future__ import annotations

from typing import Any

from ._pdf_gen import _build_table_pdf
from .security import security_overview, users_overview


def build_security_section_pdf(section: str) -> tuple[bytes, str] | None:
    overview = security_overview(limit=50)
    if section == "roles":
        title = "Reporte de roles"
        subtitle = f"Resumen de roles, descripcion, permisos y accesos visibles. Registros: {len(overview['roles'])}"
        headers = ["Rol", "Descripcion", "Permisos", "Accesos visibles"]
        rows: list[list[Any]] = [
            [
                item["role_name"],
                item.get("description", "N/D"),
                ", ".join(item.get("permission_codes", [])) or "N/D",
                ", ".join(nav["label"] for nav in item.get("access_buttons", [])) or "Sin accesos",
            ]
            for item in overview["roles"]
        ]
        return _build_table_pdf(title, subtitle, headers, rows), title
    if section == "permissions":
        title = "Reporte de permisos"
        subtitle = f"Permisos configurados para controlar accesos del sistema. Registros: {len(overview['permissions'])}"
        headers = ["Permiso", "Descripcion"]
        rows = [[item["permission_code"], item.get("description", "N/D")] for item in overview["permissions"]]
        return _build_table_pdf(title, subtitle, headers, rows), title
    if section == "sessions":
        title = "Reporte de sesiones recientes"
        subtitle = f"Sesiones emitidas por el login basico de la aplicacion. Registros: {len(overview['sessions'])}"
        headers = ["Usuario", "Activa", "Creada", "Expira"]
        rows = [
            [
                item.get("username", "N/D"),
                "Si" if item.get("is_active") else "No",
                item.get("created_at"),
                item.get("expires_at"),
            ]
            for item in overview["sessions"]
        ]
        return _build_table_pdf(title, subtitle, headers, rows), title
    if section == "activity":
        title = "Reporte de actividad reciente"
        subtitle = f"Eventos recientes registrados en user_activity_logs. Registros: {len(overview['activity'])}"
        headers = ["Accion", "Usuario", "Fecha"]
        rows = [[item.get("action", "N/D"), item.get("username") or item.get("email") or "N/D", item.get("created_at")] for item in overview["activity"]]
        return _build_table_pdf(title, subtitle, headers, rows), title
    if section == "users":
        title = "Reporte de usuarios"
        users = users_overview(limit=100)["users"]
        subtitle = f"Cuentas, rol principal y estado de activacion. Registros: {len(users)}"
        headers = ["Usuario", "Email", "Rol principal", "Activo"]
        rows = [
            [
                item.get("username", "N/D"),
                item.get("email", "N/D"),
                item.get("primary_role", "N/D"),
                "Activo" if item.get("is_active") else "Inactivo",
            ]
            for item in users
        ]
        return _build_table_pdf(title, subtitle, headers, rows), title
    return None
