from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from src.app.modules.admin.service import (
    build_security_section_pdf,
    create_ownership_user,
    delete_user,
    ensure_user_status_field,
    get_ownership_user,
    get_roles_list,
    list_ownership_users,
    role_editor_payload,
    search_hotels,
    security_overview,
    toggle_user_active,
    update_assigned_hotels,
    update_role_definition,
    users_overview,
)
from src.app.security.dependencies import require_permission


router = APIRouter(prefix="/admin", tags=["admin"])
api_router = APIRouter(prefix="/api/admin", tags=["admin-api"])


def _serialize_users_overview(current_user: dict) -> dict:
    overview = users_overview()
    current_user_id = str(current_user.get("_id") or "")
    current_username = current_user.get("username") or ""

    users = []
    for user in overview["users"]:
        user_id = str(user.get("_id") or "")
        is_current_user = user.get("username") == current_username or user_id == current_user_id
        is_protected = user.get("primary_role") == "super_admin"
        can_toggle = not is_current_user and not is_protected

        users.append(
            {
                "user_id": user_id,
                "username": user.get("username") or "",
                "email": user.get("email") or "",
                "primary_role": user.get("primary_role") or "",
                "role_names": user.get("role_names", []),
                "is_active": bool(user.get("is_active", True)),
                "created_at": user.get("created_at"),
                "display_name": user.get("display_name") or user.get("username") or "",
                "is_current_user": is_current_user,
                "is_protected": is_protected,
                "can_toggle": can_toggle,
                "toggle_label": "Desactivar" if user.get("is_active", True) else "Activar",
                "action_hint": "Sesión actual" if is_current_user else ("Protegido" if is_protected else ""),
            }
        )

    return {
        "counts": overview["counts"],
        "users": users,
        "current_user": {
            "username": current_username,
            "primary_role": current_user.get("primary_role") or "",
        },
    }


def _serialize_permissions_overview() -> dict:
    overview = security_overview()
    roles = []
    for role in overview["roles"]:
        roles.append(
            {
                "role_name": role.get("role_name") or "",
                "description": role.get("description") or "Sin descripción",
                "permission_codes": role.get("permission_codes", []),
                "access_buttons": [
                    {
                        "label": item.get("label") or "",
                        "href": item.get("href") or "",
                        "icon": item.get("icon") or "",
                    }
                    for item in role.get("access_buttons", [])
                ],
            }
        )

    permissions = [
        {
            "permission_code": permission.get("permission_code") or "",
            "description": permission.get("description") or "Sin descripción",
        }
        for permission in overview["permissions"]
    ]

    return {
        "counts": overview["counts"],
        "roles": roles,
        "permissions": permissions,
    }


@router.get("/security")
def security_dashboard(request: Request, current_user: dict = Depends(require_permission("users.manage"))):
    return _serialize_permissions_overview()


@router.get("/users")
def users_dashboard(request: Request, current_user: dict = Depends(require_permission("users.manage"))):
    ensure_user_status_field()
    return _serialize_users_overview(current_user)


@api_router.get("/users")
def users_dashboard_api(current_user: dict = Depends(require_permission("users.manage"))):
    ensure_user_status_field()
    return _serialize_users_overview(current_user)


@api_router.get("/permissions")
def permissions_dashboard_api(current_user: dict = Depends(require_permission("users.manage"))):
    ensure_user_status_field()
    return _serialize_permissions_overview()


@api_router.get("/permissions/roles/{role_name}")
def permissions_role_detail_api(role_name: str, current_user: dict = Depends(require_permission("users.manage"))):
    from src.app.modules.admin.service import role_editor_payload_api

    payload = role_editor_payload_api(role_name)
    if payload is None:
        return JSONResponse({"ok": False, "message": "Rol no encontrado."}, status_code=404)
    return payload


@api_router.put("/permissions/roles/{role_name}")
def permissions_role_update_api(
    role_name: str,
    body: dict,
    current_user: dict = Depends(require_permission("users.manage")),
):
    from src.app.modules.admin.service import update_role_definition

    description = body.get("description", "")
    permission_codes = body.get("permission_codes", [])
    result = update_role_definition(role_name, description, permission_codes, current_user)
    status_code = 200 if result["ok"] else 400
    return JSONResponse(result, status_code=status_code)


@router.get("/roles/{role_name}")
def role_editor(request: Request, role_name: str, current_user: dict = Depends(require_permission("users.manage"))):
    payload = role_editor_payload(role_name)
    if payload is None:
        return JSONResponse({"error": "Rol no encontrado."}, status_code=404)
    return payload


@router.post("/roles/{role_name}")
def role_editor_save(
    request: Request,
    role_name: str,
    description: str = Form(...),
    permission_codes: list[str] = Form(default=[]),
    current_user: dict = Depends(require_permission("users.manage")),
):
    result = update_role_definition(role_name, description, permission_codes, current_user)
    return result


@router.get("/reports/{section}.pdf")
def security_report_pdf(section: str, current_user: dict = Depends(require_permission("users.manage"))):
    result = build_security_section_pdf(section)
    if result is None:
        return JSONResponse({"error": "Sección de reporte no encontrada."}, status_code=404)
    pdf_bytes, title = result
    filename = f"{section}_report.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "X-Report-Title": title},
    )


def _toggle_user_active_redirect(user_id: str, current_user: dict) -> RedirectResponse:
    result = toggle_user_active(user_id, current_user)
    return RedirectResponse(url=f"/admin/users", status_code=303)


@router.post("/users/{user_id}/toggle-active")
def users_toggle_active_post(user_id: str, request: Request, current_user: dict = Depends(require_permission("users.manage"))):
    return _toggle_user_active_redirect(user_id, current_user)


@router.get("/users/{user_id}/toggle-active")
def users_toggle_active_get(user_id: str, request: Request, current_user: dict = Depends(require_permission("users.manage"))):
    return _toggle_user_active_redirect(user_id, current_user)


@api_router.post("/users/{user_id}/toggle-active")
def users_toggle_active_api(user_id: str, current_user: dict = Depends(require_permission("users.manage"))):
    result = toggle_user_active(user_id, current_user)
    status_code = 200 if result["ok"] else 400
    return JSONResponse(result, status_code=status_code)


@api_router.delete("/users/{user_id}")
def users_delete_api(user_id: str, current_user: dict = Depends(require_permission("users.manage"))):
    result = delete_user(user_id, current_user)
    status_code = 200 if result["ok"] else 400
    return JSONResponse(result, status_code=status_code)


# ─── Ownership Management ──────────────────────────────────────────────

@api_router.get("/ownership/users")
def ownership_users_list(current_user: dict = Depends(require_permission("users.manage"))):
    return {"users": list_ownership_users(), "roles": get_roles_list()}


@api_router.post("/ownership/users")
def ownership_users_create(
    body: dict,
    current_user: dict = Depends(require_permission("users.manage")),
):
    username = str(body.get("username", "")).strip()
    email = str(body.get("email", "")).strip().lower()
    password = str(body.get("password", ""))
    primary_role = str(body.get("primary_role", "")).strip()
    display_name = str(body.get("display_name", "")).strip() or username
    assigned_hotels = body.get("assigned_hotels", [])

    result = create_ownership_user(username, email, password, primary_role, display_name, assigned_hotels)
    status_code = 200 if result["ok"] else 400
    return JSONResponse(result, status_code=status_code)


@api_router.get("/ownership/users/{user_id}")
def ownership_users_detail(
    user_id: str,
    current_user: dict = Depends(require_permission("users.manage")),
):
    user = get_ownership_user(user_id)
    if user is None:
        return JSONResponse({"ok": False, "message": "Usuario no encontrado."}, status_code=404)
    return {"user": user}


@api_router.put("/ownership/users/{user_id}/assigned-hotels")
def ownership_update_assigned_hotels(
    user_id: str,
    body: dict,
    current_user: dict = Depends(require_permission("users.manage")),
):
    assigned_hotels = body.get("assigned_hotels", [])
    result = update_assigned_hotels(user_id, assigned_hotels)
    status_code = 200 if result["ok"] else 400
    return JSONResponse(result, status_code=status_code)


@api_router.get("/ownership/hotels/search")
def ownership_hotels_search(
    q: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    current_user: dict = Depends(require_permission("users.manage")),
):
    return search_hotels(q, page, page_size)


@api_router.get("/ownership/roles")
def ownership_roles_list(current_user: dict = Depends(require_permission("users.manage"))):
    return {"roles": get_roles_list()}
