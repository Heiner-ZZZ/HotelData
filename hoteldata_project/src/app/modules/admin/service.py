from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from textwrap import wrap
from typing import Any

from bson import ObjectId

from src.database.connection import get_database
from src.app.security.navigation import NAVIGATION_BY_ROLE, get_navigation_for_role


def _clean(document: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(document)
    for key, value in list(cleaned.items()):
        if isinstance(value, ObjectId):
            cleaned[key] = str(value)
        elif isinstance(value, list):
            cleaned[key] = [str(item) if isinstance(item, ObjectId) else item for item in value]
    cleaned.pop("password_hash", None)
    return cleaned


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def security_overview(limit: int = 20) -> dict[str, Any]:
    ensure_user_status_field()
    db = get_database()
    role_permissions = role_permission_map()
    roles = [_clean(item) for item in db.roles.find({}).sort("role_name", 1)]
    for role in roles:
        role_name = role.get("role_name")
        permissions = role_permissions.get(role_name, [])
        role["permission_codes"] = permissions
        role["access_buttons"] = get_navigation_for_role(role_name, set(permissions))
    return {
        "users": [_clean(item) for item in db.users.find({}, {"password_hash": 0}).sort("created_at", -1).limit(limit)],
        "roles": roles,
        "permissions": [_clean(item) for item in db.permissions.find({}).sort("permission_code", 1)],
        "sessions": [_clean(item) for item in db.user_sessions.find({}).sort("created_at", -1).limit(limit)],
        "activity": [_clean(item) for item in db.user_activity_logs.find({}).sort("created_at", -1).limit(limit)],
        "counts": {
            "users": db.users.count_documents({}),
            "roles": db.roles.count_documents({}),
            "permissions": db.permissions.count_documents({}),
            "sessions": db.user_sessions.count_documents({}),
            "activity": db.user_activity_logs.count_documents({}),
        },
    }


def users_overview(limit: int = 50) -> dict[str, Any]:
    ensure_user_status_field()
    db = get_database()
    users = [_clean(item) for item in db.users.find({}, {"password_hash": 0}).sort("created_at", -1).limit(limit)]
    roles = {str(item["_id"]): item.get("role_name") for item in db.roles.find({})}
    for user in users:
        user["role_names"] = [roles.get(str(role_id), str(role_id)) for role_id in user.get("role_ids", [])]
    return {
        "users": users,
        "roles": [_clean(item) for item in db.roles.find({}).sort("role_name", 1)],
        "counts": {
            "users": db.users.count_documents({}),
            "roles": db.roles.count_documents({}),
        },
    }


def role_permission_map() -> dict[str, list[str]]:
    db = get_database()
    mapping: dict[str, list[str]] = {}
    rows = list(db.role_permissions.find({}, {"_id": 0, "role_name": 1, "permission_code": 1}).sort([("role_name", 1), ("permission_code", 1)]))
    for item in rows:
        role_name = item.get("role_name")
        permission_code = item.get("permission_code")
        if not role_name or not permission_code:
            continue
        mapping.setdefault(role_name, []).append(permission_code)
    return mapping


def role_editor_payload(role_name: str) -> dict[str, Any] | None:
    db = get_database()
    role = db.roles.find_one({"role_name": role_name})
    if not role:
        return None
    role_clean = _clean(role)
    permissions = [_clean(item) for item in db.permissions.find({}).sort("permission_code", 1)]
    permission_map = role_permission_map()
    selected_codes = permission_map.get(role_name, [])
    role_clean["permission_codes"] = selected_codes
    role_clean["access_buttons"] = get_navigation_for_role(role_name, set(selected_codes))
    role_clean["navigation_catalog"] = [
        {
            "label": item["label"],
            "href": item["href"],
            "icon": item["icon"],
            "visible": any(nav["href"] == item["href"] for nav in role_clean["access_buttons"]),
        }
        for item in NAVIGATION_BY_ROLE.get(role_name, [])
    ]
    return {
        "role": role_clean,
        "permissions": permissions,
    }


def ensure_user_status_field() -> int:
    db = get_database()
    result = db.users.update_many(
        {"is_active": {"$exists": False}},
        {
            "$set": {
                "is_active": True,
                "updated_at": utc_now(),
                "updated_by": "system.ensure_user_status_field",
            }
        },
    )
    return int(result.modified_count)


def toggle_user_active(target_user_id: str, acting_user: dict[str, Any]) -> dict[str, Any]:
    db = get_database()
    if not target_user_id:
        return {"ok": False, "message": "Usuario no válido."}

    try:
        object_id = ObjectId(target_user_id)
    except Exception:
        return {"ok": False, "message": "Identificador de usuario inválido."}

    target_user = db.users.find_one({"_id": object_id})
    if not target_user:
        return {"ok": False, "message": "Usuario no encontrado."}

    if acting_user.get("_id") == target_user.get("_id"):
        return {"ok": False, "message": "No puede desactivar su propia cuenta desde esta vista."}

    if target_user.get("primary_role") == "super_admin":
        return {"ok": False, "message": "No se permite desactivar la cuenta super_admin."}

    new_state = not bool(target_user.get("is_active", True))
    db.users.update_one(
        {"_id": object_id},
        {
            "$set": {
                "is_active": new_state,
                "updated_at": utc_now(),
                "updated_by": acting_user.get("username"),
            }
        },
    )
    if not new_state:
        db.user_sessions.update_many(
            {"user_id": object_id, "is_active": True},
            {"$set": {"is_active": False, "end_reason": "user_deactivated"}},
        )

    db.user_activity_logs.insert_one(
        {
            "user_id": acting_user.get("_id"),
            "username": acting_user.get("username"),
            "email": acting_user.get("email"),
            "action": "admin.user_toggled_active",
            "module": "admin",
            "details": {
                "target_user_id": str(target_user["_id"]),
                "target_username": target_user.get("username"),
                "is_active": new_state,
            },
            "created_at": utc_now(),
        }
    )

    state_label = "activado" if new_state else "desactivado"
    return {
        "ok": True,
        "message": f"Usuario {target_user.get('username')} {state_label} correctamente.",
    }


def update_role_definition(
    role_name: str,
    description: str,
    permission_codes: list[str],
    acting_user: dict[str, Any],
) -> dict[str, Any]:
    db = get_database()
    role = db.roles.find_one({"role_name": role_name})
    if not role:
        return {"ok": False, "message": "Rol no encontrado."}

    if role_name == "super_admin":
        return {"ok": False, "message": "El rol super_admin no se modifica desde esta vista."}

    permission_docs = list(db.permissions.find({"permission_code": {"$in": permission_codes}}))
    valid_codes = sorted({item["permission_code"] for item in permission_docs if item.get("permission_code")})
    role_id = role["_id"]

    db.roles.update_one(
        {"_id": role_id},
        {
            "$set": {
                "description": description.strip(),
                "updated_at": utc_now(),
                "updated_by": acting_user.get("username"),
            }
        },
    )

    db.role_permissions.delete_many({"role_id": role_id, "permission_code": {"$nin": valid_codes}})
    for permission in permission_docs:
        db.role_permissions.update_one(
            {"role_id": role_id, "permission_id": permission["_id"]},
            {
                "$set": {
                    "role_name": role_name,
                    "permission_code": permission["permission_code"],
                    "updated_at": utc_now(),
                },
                "$setOnInsert": {"created_at": utc_now()},
            },
            upsert=True,
        )

    db.user_activity_logs.insert_one(
        {
            "user_id": acting_user.get("_id"),
            "username": acting_user.get("username"),
            "email": acting_user.get("email"),
            "action": "admin.role_updated",
            "module": "admin",
            "details": {
                "role_name": role_name,
                "permission_codes": valid_codes,
            },
            "created_at": utc_now(),
        }
    )
    return {"ok": True, "message": f"Rol {role_name} actualizado correctamente."}


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _truncate_pdf_cell(value: Any, max_chars: int) -> str:
    text = "" if value is None else str(value)
    return text if len(text) <= max_chars else text[: max_chars - 1] + "..."


def _build_table_pdf(title: str, subtitle: str, headers: list[str], rows: list[list[Any]]) -> bytes:
    page_width = 612
    page_height = 792
    margin = 42
    line_height = 14
    usable_width = page_width - (margin * 2)
    title_band_height = 34

    header_line = " | ".join(headers)
    text_lines: list[str] = [header_line, "-" * min(len(header_line), 92)]
    for row in rows or [["Sin registros disponibles"]]:
        row_text = " | ".join(
            f"{headers[index]}: {_truncate_pdf_cell(cell, 42)}" for index, cell in enumerate(row[: len(headers)])
        )
        wrapped = wrap(row_text, width=92) or [" "]
        text_lines.extend(wrapped)
        text_lines.append("")

    lines_per_page = 42
    pages = [text_lines[index : index + lines_per_page] for index in range(0, len(text_lines), lines_per_page)] or [["Sin registros disponibles"]]

    objects: list[bytes] = []
    page_ids: list[int] = []
    font_id = 1
    font_bold_id = 2
    pages_id = 3
    next_id = 4

    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    objects.append(b"<< /Type /Pages /Kids [] /Count 0 >>")

    for page_index, page_lines in enumerate(pages, start=1):
        content_lines = [
            "0.12 0.36 0.78 rg",
            f"{margin} {page_height - margin - title_band_height} {usable_width} {title_band_height} re f",
            "0.95 0.97 1 rg",
            f"{margin} {page_height - margin - title_band_height - 26} {usable_width} 22 re f",
            "0.85 0.89 0.94 RG",
            f"{margin} 70 {usable_width} {page_height - 170} re S",
            "BT",
            f"/F2 20 Tf {margin + 12} {page_height - margin - 24} Td ({_pdf_escape(title)}) Tj",
            "ET",
            "BT",
            f"/F1 10 Tf {margin + 12} {page_height - margin - 48} Td ({_pdf_escape(subtitle)}) Tj",
            "ET",
            "BT",
            f"/F1 9 Tf {page_width - margin - 72} {page_height - margin - 48} Td (Pagina {page_index}/{len(pages)}) Tj",
            "ET",
        ]

        cursor_y = page_height - 112
        for line_index, line in enumerate(page_lines):
            if line_index == 0:
                content_lines.extend(
                    [
                        "0.16 0.22 0.35 rg",
                        f"{margin + 10} {cursor_y} 0 0 re f",
                        "BT",
                        f"/F2 10 Tf {margin + 10} {cursor_y} Td ({_pdf_escape(line)}) Tj",
                        "ET",
                    ]
                )
            else:
                content_lines.extend(
                    [
                        "BT",
                        f"/F1 9 Tf {margin + 10} {cursor_y} Td ({_pdf_escape(line)}) Tj",
                        "ET",
                    ]
                )
            cursor_y -= line_height

        stream = "\n".join(content_lines).encode("latin-1", errors="replace")
        content_obj = f"<< /Length {len(stream)} >>\nstream\n".encode("latin-1") + stream + b"\nendstream"
        content_id = next_id
        next_id += 1
        page_id = next_id
        next_id += 1
        objects.append(content_obj)
        objects.append(
            f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {page_width} {page_height}] /Resources << /Font << /F1 {font_id} 0 R /F2 {font_bold_id} 0 R >> >> /Contents {content_id} 0 R >>".encode(
                "latin-1"
            )
        )
        page_ids.append(page_id)

    objects[pages_id - 1] = f"<< /Type /Pages /Kids [{' '.join(f'{pid} 0 R' for pid in page_ids)}] /Count {len(page_ids)} >>".encode("latin-1")
    catalog_id = next_id
    objects.append(f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode("latin-1"))

    buffer = BytesIO()
    buffer.write(b"%PDF-1.4\n")
    offsets = [0]
    for object_id, payload in enumerate(objects, start=1):
        offsets.append(buffer.tell())
        buffer.write(f"{object_id} 0 obj\n".encode("latin-1"))
        buffer.write(payload)
        buffer.write(b"\nendobj\n")
    xref_position = buffer.tell()
    buffer.write(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    buffer.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        buffer.write(f"{offset:010d} 00000 n \n".encode("latin-1"))
    buffer.write(f"trailer\n<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\nstartxref\n{xref_position}\n%%EOF".encode("latin-1"))
    return buffer.getvalue()


def build_security_section_pdf(section: str) -> tuple[bytes, str] | None:
    overview = security_overview(limit=50)
    if section == "roles":
        title = "Reporte de roles"
        subtitle = f"Resumen de roles, descripcion, permisos y accesos visibles. Registros: {len(overview['roles'])}"
        headers = ["Rol", "Descripcion", "Permisos", "Accesos visibles"]
        rows = [
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
