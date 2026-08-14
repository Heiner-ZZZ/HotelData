from __future__ import annotations

import logging
from typing import Any

from datetime import datetime

from fastapi import APIRouter, Body, Depends, Form, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from src.app.security.permissions import READ_DEP_ACTIONS
from src.app.security.session import ensure_utc

_logger = logging.getLogger(__name__)

from src.app.modules.admin.schemas import (
    NavigationNodeResponse,
    NavigationResponse,
    PermissionsOverviewResponse,
    UsersOverviewResponse,
)

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
    update_user,
    update_assigned_hotels,
    update_role_definition,
    users_overview,
)
from src.app.modules.admin.service.ownership import _resolve_hotel_names
from src.app.security.dependencies import require_permission, require_login
from src.app.security.role_helpers import get_role_name


router = APIRouter(prefix="/admin", tags=["admin"])
api_router = APIRouter(prefix="/api/admin", tags=["admin-api"])

# Actions whose grant implies the resource's ``read`` permission. Any other
# action (e.g. the compound ``hotel.manage_roles``) is a standalone code that
# must pass through the preview unchanged. Shared constant with the save
# path (admin/service/role_update.py) — see src/app/security/permissions.py.
_PREVIEW_READ_DEP_ACTIONS = READ_DEP_ACTIONS


def _filter_preview_codes(codes: set[str], available_codes: set[str]) -> set[str]:
    """Keep only grantable codes for the navigation preview.

    A code survives when it is the super-admin wildcard, a ``read`` permission,
    a compound action that does not require a sibling ``<resource>.read``
    (e.g. ``hotel.manage_roles`` — the only code behind the "Equipo y
    permisos" nav item), or a CRUD action whose ``<resource>.read`` exists in
    the catalog.

    Regression: the previous inline filter dropped ``hotel.manage_roles``
    (``hotel.read`` does not exist) so the nav preview flipped "Equipo y
    permisos" to Oculto after any edit, even for roles that legitimately hold
    the code.
    """
    return {
        code
        for code in codes
        if code == "*.*"
        or (
            code in available_codes
            and (
                "." not in code
                or code.split(".", 1)[1] == "read"
                or code.split(".", 1)[1] not in _PREVIEW_READ_DEP_ACTIONS
                or f"{code.split('.', 1)[0]}.read" in available_codes
            )
        )
    }


def _serialize_users_overview(current_user: dict) -> dict:
    overview = users_overview()
    current_user_id = str(current_user.get("_id") or "")
    current_username = current_user.get("username") or ""

    users = []
    for user in overview["users"]:
        user_id = str(user.get("_id") or "")
        is_current_user = user.get("username") == current_username or user_id == current_user_id
        is_protected = get_role_name(user) == "super_admin"
        can_toggle = not is_current_user and not is_protected

        assigned = user.get("assigned_hotels", []) or []
        users.append(
            {
                "user_id": user_id,
                "username": user.get("username") or "",
                "email": user.get("email") or "",
                "primary_role": get_role_name(user),
                "role_names": user.get("role_names", []),
                "is_active": bool(user.get("is_active", True)),
                "created_at": user.get("created_at"),
                "display_name": user.get("display_name") or user.get("username") or "",
                "assigned_hotels": [
                    {"prop_id": h["prop_id"], "label": h["label"]}
                    for h in _resolve_hotel_names(assigned)
                ],
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
            "primary_role": get_role_name(current_user),
        },
        "roles": [
            {
                "role_name": role.get("role_name") or "",
                "description": role.get("description") or "",
            }
            for role in overview.get("roles", [])
        ],
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


@api_router.get("/users", response_model=UsersOverviewResponse)
def users_dashboard_api(current_user: dict = Depends(require_permission("users.manage"))):
    ensure_user_status_field()
    return UsersOverviewResponse.model_validate(_serialize_users_overview(current_user))


@api_router.get("/permissions", response_model=PermissionsOverviewResponse)
def permissions_dashboard_api(current_user: dict = Depends(require_permission("users.manage"))):
    ensure_user_status_field()
    return PermissionsOverviewResponse.model_validate(_serialize_permissions_overview())


@api_router.post("/permissions/preview")
def permissions_permissions_preview_api(
    body: dict = Body(...),
    current_user: dict = Depends(require_permission("users.manage")),
):
    """Preview navigation for unsaved permission changes.

    This endpoint intentionally performs no write. It expands ``manage``
    permissions and asks the Mongo-backed navigation catalog which entries
    would be visible for the proposed permission set.
    """
    from src.app.security.navigation import get_all_navigation_items
    from src.app.security.permissions import ensure_read_dependencies, expand_permissions
    from src.database.connection import get_database

    raw_codes = body.get("permission_codes", [])
    if not isinstance(raw_codes, list):
        raw_codes = []
    permission_codes = {str(code).strip() for code in raw_codes if str(code).strip()}
    available_codes = {
        item.get("permission_code")
        for item in get_database().permissions.find({}, {"permission_code": 1})
        if item.get("permission_code")
    }
    normalized_codes = ensure_read_dependencies(permission_codes, available_codes)
    normalized_codes = _filter_preview_codes(normalized_codes, available_codes)
    expanded_codes = expand_permissions(normalized_codes)
    return {"navigation_catalog": get_all_navigation_items(expanded_codes)}


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
    toggle_user_active(user_id, current_user)
    return RedirectResponse(url="/admin/users", status_code=303)


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


@api_router.put("/users/{user_id}")
def users_update_api(
    user_id: str,
    body: dict,
    current_user: dict = Depends(require_permission("users.update")),
):
    """Edit a user's data from the system-admin view.

    Gated by ``users.update`` (covered by ``users.manage`` via wildcard
    expansion and by ``*.*`` for super_admin). Whitelisted fields live in
    ``admin/service/users.py::update_user``.
    """
    result = update_user(user_id, body, current_user)
    status_code = 200 if result["ok"] else 400
    return JSONResponse(result, status_code=status_code)


# ─── Ownership Management ──────────────────────────────────────────────

@api_router.get("/notifications")
def notifications_list_api(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
    notification_type: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    current_user: dict = Depends(require_login),
):
    try:
        from src.database.connection import get_database
        from src.app.security.permissions import user_has_permission

        db = get_database()
        match: dict[str, Any] = {}

        has_manage = user_has_permission(db, current_user, "users.manage")
        if not has_manage:
            user_email = (current_user.get("email") or current_user.get("username") or "").strip()
            match["recipient_email"] = {"$regex": f"^{user_email}$", "$options": "i"}
        if notification_type:
            match["notification_type"] = notification_type

        date_filter: dict[str, datetime] = {}
        if start_date:
            try:
                date_filter["$gte"] = ensure_utc(datetime.fromisoformat(start_date))
            except ValueError:
                pass
        if end_date:
            try:
                dt = ensure_utc(datetime.fromisoformat(end_date))
                date_filter["$lte"] = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
            except ValueError:
                pass
        if date_filter:
            match["created_at"] = date_filter

        total = db.notification_log.count_documents(match)
        items = list(
            db.notification_log.find(match, {"_id": 0})
            .sort([("created_at", -1)])
            .skip((page - 1) * page_size)
            .limit(page_size)
        )

        stats_pipeline: list[dict[str, Any]] = []
        if match:
            stats_pipeline.append({"$match": match})
        stats_pipeline.append({"$group": {"_id": "$notification_type", "count": {"$sum": 1}}})
        stats_pipeline.append({"$sort": {"count": -1}})
        stats = list(db.notification_log.aggregate(stats_pipeline))
        type_counts: dict[str, int] = {r["_id"]: r["count"] for r in stats}

        status_pipeline: list[dict[str, Any]] = []
        if match:
            status_pipeline.append({"$match": match})
        status_pipeline.append({"$group": {"_id": "$status", "count": {"$sum": 1}}})
        status_stats = list(db.notification_log.aggregate(status_pipeline))
        status_counts: dict[str, int] = {r["_id"]: r["count"] for r in status_stats}

        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": max(1, (total + page_size - 1) // page_size) if total else 1,
            "stats": {
                "total": total,
                "by_type": type_counts,
                "by_status": status_counts,
            },
        }
    except Exception:
        _logger.exception("Failed to fetch notifications")
        return JSONResponse(
            status_code=500,
            content={
                "items": [],
                "page": page,
                "page_size": page_size,
                "total": 0,
                "total_pages": 1,
                "stats": {"total": 0, "by_type": {}, "by_status": {}},
                "error": "Failed to load notifications",
            },
        )


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


# ─── Navigation (sidebar menu driven by permissions) ────────────────────

@api_router.get("/navigation", response_model=NavigationResponse)
def navigation_items_api(request: Request, current_user: dict = Depends(require_login)):
    """Return all navigation nodes with a ``visible`` flag based on the
    current user's expanded permission set.

    Uses the already-computed ``request.state.permission_codes`` (set by
    the role_access_middleware) to avoid redundant DB queries."""
    from src.app.security.navigation import get_all_navigation_items

    codes = getattr(request.state, "permission_codes", set())
    items = get_all_navigation_items(codes)
    return NavigationResponse(items=[NavigationNodeResponse.model_validate(i) for i in items])
