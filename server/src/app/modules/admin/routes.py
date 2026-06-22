from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from src.app.template_utils import templates

from src.app.modules.admin.service import (
    build_security_section_pdf,
    ensure_user_status_field,
    role_editor_payload,
    security_overview,
    toggle_user_active,
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
    return templates.TemplateResponse(
        request,
        "admin/security.html",
        {
            "current_user": current_user,
            "overview": security_overview(),
        },
    )


@router.get("/users")
def users_dashboard(request: Request, current_user: dict = Depends(require_permission("users.manage"))):
    ensure_user_status_field()
    return templates.TemplateResponse(
        request,
        "admin/users.html",
        {
            "current_user": current_user,
            "overview": users_overview(),
            "message": request.query_params.get("message", ""),
            "error": request.query_params.get("error", ""),
        },
    )


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
        return RedirectResponse(url="/admin/security?error=Rol no encontrado.", status_code=303)
    return templates.TemplateResponse(
        request,
        "admin/role_edit.html",
        {
            "current_user": current_user,
            "payload": payload,
            "message": request.query_params.get("message", ""),
            "error": request.query_params.get("error", ""),
        },
    )


@router.post("/roles/{role_name}")
def role_editor_save(
    request: Request,
    role_name: str,
    description: str = Form(...),
    permission_codes: list[str] = Form(default=[]),
    current_user: dict = Depends(require_permission("users.manage")),
):
    result = update_role_definition(role_name, description, permission_codes, current_user)
    param = "message" if result["ok"] else "error"
    return RedirectResponse(url=f"/admin/roles/{role_name}?{urlencode({param: result['message']})}", status_code=303)


@router.get("/reports/{section}.pdf")
def security_report_pdf(section: str, current_user: dict = Depends(require_permission("users.manage"))):
    result = build_security_section_pdf(section)
    if result is None:
        return RedirectResponse(url="/admin/security?error=Sección de reporte no encontrada.", status_code=303)
    pdf_bytes, title = result
    filename = f"{section}_report.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"', "X-Report-Title": title},
    )


def _toggle_user_active_redirect(user_id: str, current_user: dict) -> RedirectResponse:
    result = toggle_user_active(user_id, current_user)
    param = "message" if result["ok"] else "error"
    return RedirectResponse(url=f"/admin/users?{urlencode({param: result['message']})}", status_code=303)


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
